# SPDX-License-Identifier: Apache-2.0 AND CC-BY-NC-4.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Necessary packages
import networkx as nx
from networkx import algorithms
from networkx.algorithms import community
import cudaq
from cudaq import spin
from cudaq.qis import *
import numpy as np
from mpi4py import MPI
from typing import List


# Getting information about platform
cudaq.set_target("nvidia")
target = cudaq.get_target()

# Setting up MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
num_qpus = comm.Get_size()

# Define a function to generate the Hamiltonian for a max cut problem using the graph G
def hamiltonian_max_cut(sources : List[int], targets : List[int], weights : List[float]): 
    """Hamiltonian for finding the max cut for the graph  with edges defined by the pairs generated by source and target edges
        
    Parameters
    ----------
    sources: List[int] 
        list of the source vertices for edges in the graph
    targets: List[int]
        list of the target vertices for the edges in the graph
    weights : List[float]
        list of the weight of the edge determined by the source and target with the same index
    Returns
    -------
    cudaq.SpinOperator
        Hamiltonian for finding the max cut of the graph defined by the given edges
    """
    # Edit the code below
    
    
    
    
    
    
    
    
    # Edit the code above
    return hamiltonian

# Problem Kernel

@cudaq.kernel
def qaoaProblem(qubit_0 : cudaq.qubit, qubit_1 : cudaq.qubit, alpha : float):
    """Build the QAOA gate sequence between two qubits that represent an edge of the graph
    Parameters
    ----------
    qubit_0: cudaq.qubit 
        Qubit representing the first vertex of an edge
    qubit_1: cudaq.qubit 
        Qubit representing the second vertex of an edge
    alpha: float
        Free variable   

    """
    x.ctrl(qubit_0, qubit_1)
    rz(2.0*alpha, qubit_1)
    x.ctrl(qubit_0, qubit_1)

# Mixer Kernel
@cudaq.kernel
def qaoaMixer(qubit_0 : cudaq.qubit, beta : float):
    """Build the QAOA gate sequence that is applied to each qubit in the mixer portion of the circuit
    Parameters
    ----------
    qubit_0: cudaq.qubit 
        Qubit 
    beta: float
        Free variable   

    """
    rx(2.0*beta, qubit_0)


# We now define the kernel_qaoa function which will be the QAOA circuit for our graph
# Since the QAOA circuit for max cut depends on the structure of the graph, 
# we'll feed in global concrete variable values into the kernel_qaoa function for the qubit_count, layer_count, edges_src, edges_tgt.
# The types for these variables are restricted to Quake Values (e.g. qubit, int, List[int], ...)
# The thetas plaeholder will be our free parameters (the alphas and betas in the circuit diagrams depicted above)
@cudaq.kernel
def kernel_qaoa(qubit_count :int, layer_count: int, edges_src: List[int], edges_tgt: List[int], thetas : List[float]):
    """Build the QAOA circuit for max cut of the graph with given edges and nodes
    Parameters
    ----------
    qubit_count: int 
        Number of qubits in the circuit, which is the same as the number of nodes in our graph
    layer_count : int 
        Number of layers in the QAOA kernel
    edges_src: List[int]
        List of the first (source) node listed in each edge of the graph, when the edges of the graph are listed as pairs of nodes
    edges_tgt: List[int]
        List of the second (target) node listed in each edge of the graph, when the edges of the graph are listed as pairs of nodes
    thetas: List[float]
        Free variables to be optimized   

    """
    # Let's allocate the qubits
    qreg = cudaq.qvector(qubit_count)
    
    # And then place the qubits in superposition
    h(qreg)
    
    # Each layer has two components: the problem kernel and the mixer
    for i in range(layer_count):
        # Add the problem kernel to each layer
        for edge in range(len(edges_src)):
            qubitu = edges_src[edge]
            qubitv = edges_tgt[edge]
            qaoaProblem(qreg[qubitu], qreg[qubitv], thetas[i])
        # Add the mixer kernel to each layer
        for j in range(qubit_count):
            qaoaMixer(qreg[j],thetas[i+layer_count])

def find_optimal_parameters(G, layer_count, seed):
    """Function for finding the optimal parameters of QAOA for the max cut of a graph
    Parameters
    ----------
    G: networkX graph 
        Problem graph whose max cut we aim to find
    layer_count : int 
        Number of layers in the QAOA circuit
    seed : int
        Random seed for reproducibility of results
        
    Returns
    -------
    list[float]
        Optimal parameters for the QAOA applied to the given graph G
    """
   

    # Problem parameters
    nodes = sorted(list(nx.nodes(G)))
    qubit_src = []
    qubit_tgt = []
    weights = []
    for u, v in nx.edges(G):
        # We can use the index() command to read out the qubits associated with the vertex u and v.
        qubit_src.append(nodes.index(u))
        qubit_tgt.append(nodes.index(v))
        weights.append(G.edges[u,v]['weight'])                                           
    # The number of qubits we'll need is the same as the number of vertices in our graph
    qubit_count : int = len(nodes)
    # Each layer of the QAOA kernel contains 2 parameters
    parameter_count : int = 2*layer_count # edit this line if more parameters are added to each layer of the qaoa kernel
    
    # Specify the optimizer and its initial parameters. 
    optimizer = cudaq.optimizers.COBYLA() # Edit this line to change the optimizer
    np.random.seed(seed)
    cudaq.set_random_seed(seed)
    optimizer.initial_parameters = np.random.uniform(-np.pi, np.pi,
                                                     parameter_count)   

    # Pass the kernel, spin operator, and optimizer to `cudaq.vqe`.
    optimal_expectation, optimal_parameters = cudaq.vqe(
        kernel=kernel_qaoa,
        spin_operator=hamiltonian_max_cut(qubit_src, qubit_tgt, weights),
        argument_mapper=lambda parameter_vector: (qubit_count, layer_count, qubit_src, qubit_tgt, parameter_vector),
        optimizer=optimizer,
        parameter_count=parameter_count) # the lines above will need editing if the optimizer is changed to a gradient-based optimizer

    return optimal_parameters

# These function from Lab 2 are used to identify the subgraph
# that contains a given vertex, and identify the vertices of the parent graph 
# that lie on the border of the subgraphs in the subgraph dictionary

def subgraph_of_vertex(graph_dictionary, vertex):
    """
    A function that takes as input a subgraph partition (in the form of a graph dictionary) and a vertex.
    The function should return the key associated with the subgraph that contains the given vertex.
    
    Parameters
    ----------
    graph_dictionary: dict of networkX.Graph with str as keys 
    v : int
        v is a name for a vertex

    Returns
    -------
    str
        the key associated with the subgraph that contains the given vertex.
    """
    # in case a vertex does not appear in the graph_dictionary, return the empty string
    location = '' 

    for key in graph_dictionary:
        if vertex in graph_dictionary[key].nodes():
            location = key
    return location

def border(G, subgraph_dictionary):
    """Build a graph made up of border vertices from the subgraph partition
    
    Parameters
    ----------
    G: networkX.Graph 
        Graph whose max cut we want to find
    subgraph_dictionary: dict of networkX graph with str as keys 
        Each graph in the dictionary should be a subgraph of G
        
    Returns
    -------
    networkX.Graph
        Subgraph of G made up of only the edges connecting subgraphs in the subgraph dictionary
    """   
    borderGraph = nx.Graph()
    for u,v in G.edges():
        border = True
        for key in subgraph_dictionary:
            SubG = subgraph_dictionary[key]
            edges = list(nx.edges(SubG))
            if (u,v) in edges:
                border = False
        if border==True:
            borderGraph.add_edge(u,v)
        
    return borderGraph

def cutvalue(G):
    """Returns the cut value of G based on the coloring of the nodes of G
    
    Parameters
    ----------
    G: networkX.Graph 
        Graph with weighted edges and with binary value colors assigned to the vertices
    Returns
    -------
    int 
        cut value of the graph determined by the vertex colors and edge weights
    """  
    # Edit the code below
  
  
  
  
    # Edit the code above
    return cut

def subgraphpartition(G,n, name, globalGraph):
    """Divide the graph up into at most n subgraphs
    
    Parameters
    ----------
    G: networkX.Graph 
        Graph that we want to subdivivde which lives inside of or is equatl to globalGraph
    n : int
        n is the maximum number of subgraphs in the partition
    name : str
        prefix for the graphs (in our case we'll use 'Global')
    globalGraph: networkX.Graph
        original problem graph
        
    Returns
    -------
    dict of str : networkX.Graph
        Dictionary of networkX graphs with a string as the key
    """
    greedy_partition = community.greedy_modularity_communities(G, weight='weight', resolution=1.1, cutoff=1, best_n=n)
    number_of_subgraphs = len(greedy_partition)

    graph_dictionary = {}
    graph_names=[]
    for i in range(number_of_subgraphs):
        subgraphname=name+':'+str(i)
        graph_names.append(subgraphname)

    for i in range(number_of_subgraphs):
        nodelist = sorted(list(greedy_partition[i]))
        graph_dictionary[graph_names[i]] = nx.subgraph(globalGraph, nodelist)
     
    return(graph_dictionary) 


def qaoa_for_graph(G, layer_count, shots, seed):
    """Function for finding the max cut of a graph using QAOA
    
    Parameters
    ----------
    G: networkX graph 
        Problem graph whose max cut we aim to find
    layer_count : int 
        Number of layers in the QAOA circuit
    shots : int
        Number of shots in the sampling subroutine
    seed : int
        Random seed for reproducibility of results

    Returns
    -------
    str
        Binary string representing the max cut coloring of the vertinces of the graph
    """
    if nx.number_of_nodes(G) ==1 or nx.number_of_edges(G) ==0: 
        # The first condition implies the second condition so we really don't need 
        # to consider the case nx.number_of_nodes(G) ==1
        results = ''
        for u in list(nx.nodes(G)):
            np.random.seed(seed)
            random_assignment = str(np.random.randint(0, 1))
            results+=random_assignment
        
    else:
        parameter_count: int = 2 * layer_count # edit this line if more parameters are added to each layer of the qaoa kernel

        # Problem parameters
        nodes = sorted(list(nx.nodes(G)))
        qubit_src = []
        qubit_tgt = []
        for u, v in nx.edges(G):
            # We can use the index() command to read out the qubits associated with the vertex u and v.
            qubit_src.append(nodes.index(u))
            qubit_tgt.append(nodes.index(v))
        # The number of qubits we'll need is the same as the number of vertices in our graph
        qubit_count : int = len(nodes)
        # Each layer of the QAOA kernel contains 2 parameters
        parameter_count : int = 2*layer_count
    
        optimal_parameters = find_optimal_parameters(G, layer_count, seed)

        # Print the optimized parameters
        print("Optimal parameters = ", optimal_parameters)
        cudaq.set_random_seed(seed)
        # Sample the circuit
        counts = cudaq.sample(kernel_qaoa, qubit_count, layer_count, qubit_src, qubit_tgt, optimal_parameters, shots_count=shots)
        print('most_probable outcome = ',counts.most_probable())
        results = str(counts.most_probable())
    return results
    
# The functions below are based on code from Lab 2
# Define the mergerGraph for a given border graph and subgraph
# partitioning. And color code the vertices
# according to the subgraph that the vertex represents
def createMergerGraph(border, subgraphs):
    """Build a graph containing a vertex for each subgraph 
    and edges between vertices are added if there is an edge between
    the corresponding subgraphs
    
    Parameters
    ----------
    border : networkX.Graph 
        Graph of connections between vertices in distinct subgraphs
    subgraphs : dict of networkX graph with str as keys 
        The nodes of border should be a subset of the the graphs in the subgraphs dictionary
        
    Returns
    -------
    networkX.Graph
        Merger graph containing a vertex for each subgraph 
        and edges between vertices are added if there is an edge between
        the corresponding subgraphs
    """ 
    M = nx.Graph()
    
    for u, v in border.edges():
        subgraph_id_for_u = subgraph_of_vertex(subgraphs, u)
        subgraph_id_for_v = subgraph_of_vertex(subgraphs, v)
        if subgraph_id_for_u != subgraph_id_for_v:
            M.add_edge(subgraph_id_for_u, subgraph_id_for_v)   
    return M


# Compute the penalties for edges in the supplied mergerGraph
# for the subgraph partitioning of graph G
def merger_graph_penalties(mergerGraph, subgraph_dictionary, G):
    """Compute penalties for the edges in the mergerGraph and add them
    as edge attributes.
    
    Parameters
    ----------
    mergerGraph : networkX.Graph 
        Graph of connections between vertices in distinct subgraphs of G
    subgraph_dictionary : dict of networkX graph with str as keys 
        subgraphs of G that are represented as nodes in the mergerGraph
    G : networkX.Graph
        graph whose vertices has an attribute 'color'
    
    Returns
    -------
    networkX.Graph
        Merger graph containing penalties
    """ 
    # Edit the code below
    
   
   
   
   
   
   
   
   
    # Edit the code below
    return mergerGraph


# Define the Hamiltonian for applying QAOA during the merger stage
# The variables s_i are defined so that s_i = 1 means we will not 
# flip the subgraph Gi's colors and s_i = -1 means we will flip the colors of subgraph G_i
def mHamiltonian(merger_edge_src, merger_edge_tgt, penalty):
    """Hamiltonian for finding the optimal swap schedule for the subgraph partitioning encoded in the merger graph
        
    Parameters
    ----------
    merger_edge_src: List[int] 
        list of the source vertices of edges of a graph
    merger_edge_tgt: List[int]
        list of target vertices of edges of a graph
    penalty: List[int]
        list of penalty terms associated with the edge determined by the source and target vertex of the same index

    Returns
    -------
    cudaq.SpinOperator
        Hamiltonian for finding the optimal swap schedule for the subgraph partitioning encoded in the merger graph
    """  
    mergerHamiltonian = 0
    
 # Add Hamiltonian terms for edges within a subgraph that contain a border element
    for i in range(len(merger_edge_src)):
        # Add a term to the Hamiltonian for the edge (u,v)
        qubitu = merger_edge_src[i]
        qubitv = merger_edge_tgt[i]
        mergerHamiltonian+= -penalty[i]*(spin.z(qubitu))*(spin.z(qubitv))
    return mergerHamiltonian

# A function to carry out QAOA during the merger stage of the
# divide-and-conquer QAOA algorithm for graph G, its subgraphs (graph_dictionary)
# and merger_graph 

def merging(G, graph_dictionary, merger_graph):
    """
    Using QAOA, identify which subgraphs should be in the swap schedule (e.g. which subgraphs will require
    flipping of the colors when merging the subgraph solutions into a solution of the graph G
    
    Parameters
    ----------
    G : networkX.Graph 
        Graph with vertex color attributes
    graph_dictionary : dict of networkX graph with str as keys 
        subgraphs of G
    mergerGraph : networkX.Graph
        Graph whose vertices represent subgraphs in the graph_dictionary

    Returns
    -------
    str
        returns string of 0s and 1s indicating which subgraphs should have their colors swapped
    """  
    
    merger_graph_with_penalties = merger_graph_penalties(merger_graph,graph_dictionary, G)
    # In the event that the merger penalties are not trivial, run QAOA, else don't flip any graph colors
    if (True in (merger_graph_with_penalties[u][v]['penalty'] != 0 for u, v in nx.edges(merger_graph_with_penalties))): 
        
        penalty = []
        merger_edge_src = []
        merger_edge_tgt = []
        merger_nodes = sorted(list(merger_graph_with_penalties.nodes()))
        for u, v in nx.edges(merger_graph_with_penalties):
            # We can use the index() command to read out the qubits associated with the vertex u and v.
            merger_edge_src.append(merger_nodes.index(u))
            merger_edge_tgt.append(merger_nodes.index(v))
            penalty.append(merger_graph_with_penalties[u][v]['penalty'])
            
        merger_Hamiltonian = mHamiltonian(merger_edge_src, merger_edge_tgt, penalty)
        
        # Run QAOA on the merger subgraph to identify which subgraphs
        # if any should change colors
        layer_count_merger = 1 # Edit this line to change the layer count
        parameter_count_merger: int = 2 * layer_count_merger
        merger_seed = 12345 # Edit this line to change the seed for the merger call to QAOA
        nodes_merger = sorted(list(nx.nodes(merger_graph)))
        merger_edge_src = []
        merger_edge_tgt = []
        for u, v in nx.edges(merger_graph_with_penalties):
            # We can use the index() command to read out the qubits associated with the vertex u and v.
            merger_edge_src.append(nodes_merger.index(u))
            merger_edge_tgt.append(nodes_merger.index(v))
        # The number of qubits we'll need is the same as the number of vertices in our graph
        qubit_count_merger : int = len(nodes_merger)

        # Specify the optimizer and its initial parameters. Make it repeatable.
        cudaq.set_random_seed(merger_seed)
        optimizer_merger = cudaq.optimizers.COBYLA() # Edit this line to change the optimizer
        np.random.seed(merger_seed)
        optimizer_merger.initial_parameters = np.random.uniform(-np.pi, np.pi,
                                                     parameter_count_merger)  
        optimizer_merger.max_iterations=150
        # Pass the kernel, spin operator, and optimizer to `cudaq.vqe`.
        optimal_expectation, optimal_parameters = cudaq.vqe(
            kernel=kernel_qaoa,
            spin_operator=merger_Hamiltonian,
            argument_mapper=lambda parameter_vector: (qubit_count_merger, layer_count_merger, merger_edge_src, merger_edge_tgt, parameter_vector),
            optimizer=optimizer_merger,
            parameter_count=parameter_count_merger, 
            shots = 20000) # the lines above will need editing if the optimizer is changed to a gradient-based optimizer

        # Sample the circuit using the optimized parameters
        # Sample enough times to distinguish the most_probable outcome for
        # merger graphs with 12 vertices
        sample_number=20000
        counts = cudaq.sample(kernel_qaoa, qubit_count_merger, layer_count_merger, merger_edge_src, merger_edge_tgt, optimal_parameters, shots_count=sample_number)
        mergerResultsString = str(counts.most_probable())
        
    else:
        mergerResultsList = [0]*nx.number_of_nodes(merger_graph)
        mergerResultsString = ''.join(str(x) for x in mergerResultsList)
        print('Merging stage is trivial')
    return mergerResultsString



# Next we define some functions to keep track of the unaltered cuts 
# (recorded as unaltered_colors) and the merged cuts (recorded as new_colors).  
# The new_colors are derived from flipping the colors
# of all the nodes in a subgraph based on the flip_colors variable which
# captures the solution to the merger QAOA problem.

def unaltered_colors(G, graph_dictionary, max_cuts):
    """Adds colors to each vertex, v, of G based on the color of v in the subgraph containing v which is
    read from the max_cuts dictionary
        
    Parameters
    ----------
    G : networkX.Graph 
        Graph with vertex color attributes
    subgraph_dictionary : dict of networkX graph with str as keys 
        subgraphs of G 
    max_cuts : dict of str
        dictionary of node colors for subgraphs in the subgraph_dictionary

    Returns
    -------
    networkX.Graph, str
        returns G with colored nodes
    """  
    subgraphColors={}

    
    for key in graph_dictionary:
        SubG = graph_dictionary[key]
        sorted_subgraph_nodes = sorted(list(nx.nodes(SubG)))
        for v in sorted_subgraph_nodes:
            G.nodes[v]['color']=max_cuts[key][sorted_subgraph_nodes.index(v)]
    # returns the input graph G with a coloring of the nodes based on the unaltered merger
    # of the max cut solutions of the subgraphs in the graph_dictionary
    return G

def new_colors(graph_dictionary, G, mergerGraph, flip_colors):
    """For each subgraph in the flip_colors list, changes the color of all the vertices in that subgraph
    and records this information in the color attribute of G
        
    Parameters
    ----------
    graph_dictionary : dict of networkX graph with str as keys 
        subgraphs of G
    G : networkX.Graph 
        Graph with vertex color attributes
    mergerGraph: networkX.Graph
        Graph whose vertices represent subgraphs in the graph_dictionary
    flip_colors : dict of str
        dictionary of binary strings for subgraphs in the subgraph_dictionary
        key:0 indicates the node colors remain fixed in subgraph called key 
        key:1 indicates the node colors should be flipped in subgraph key

    Returns
    -------
    networkX.Graph, str
        returns G with the revised vertex colors
    """  
    flipGraphColors={}
    mergerNodes = sorted(list(nx.nodes(mergerGraph)))
    for u in mergerNodes:
        indexu = mergerNodes.index(u)
        flipGraphColors[u]=int(flip_colors[indexu])
   
    for key in graph_dictionary:
        if flipGraphColors[key]==1:
            for u in graph_dictionary[key].nodes():
                G.nodes[u]['color'] = str(1 - int(G.nodes[u]['color']))
    
    revised_colors = ''
    for u in sorted(G.nodes()):
        revised_colors += str(G.nodes[u]['color'])
    
    return G, revised_colors


def subgraph_solution(G, key, vertex_limit, subgraph_limit, layer_count, global_graph,seed ):
    """
    Recursively finds max cut approximations of the subgraphs of the global_graph
    Parameters
    ----------
    G : networkX.Graph 
        Graph with vertex color attributes
    key : str
        name of subgraph
    vertex_limit : int
        maximum size of graph to which QAOA will be applied directly
    subgraph_limit : int
        maximum size of the merger graphs, or maximum number of subgraphs in any subgraph decomposition 
    layer_count : int
        number of layers in QAOA circuit for finding max cut solutions
    global_graph : networkX.Graph
        the parent graph
    seed : int
        random seed for reproducibility

    Returns
    -------
    str
        returns string of 0s and 1s representing colors of vertices of global_graph for the approx max cut solution
    """  
    results ={}
    # Find the max cut of G using QAOA, provided G is small enough
    if nx.number_of_nodes(G)<vertex_limit+1:
        print('Working on finding max cut approximations for ',key)
        
        result =qaoa_for_graph(G, seed=seed, shots = 10000, layer_count=layer_count)
        results[key]=result
        # color the global graph's nodes according to the results
        nodes_of_G = sorted(list(G.nodes()))
        for u in G.nodes():
            global_graph.nodes[u]['color']=results[key][nodes_of_G.index(u)]
        return result
    else: # Recursively apply the algorithm in case G is too big
        # Divide the graph and identify the subgraph dictionary
        subgraph_limit =min(subgraph_limit, nx.number_of_nodes(G) )
        subgraph_dictionary = subgraphpartition(G,subgraph_limit, str(key), global_graph)
        
        # Conquer: solve the subgraph problems recursively
        for skey in subgraph_dictionary:
            results[skey]=subgraph_solution(subgraph_dictionary[skey], skey, vertex_limit, subgraph_limit, \
                                            layer_count, global_graph, seed )
            
        print('Found max cut approximations for ',list(subgraph_dictionary.keys()))
        
       
        # Color the nodes of G to indicate subgraph max cut solutions
        G = unaltered_colors(G, subgraph_dictionary, results)
        unaltered_cut_value = cutvalue(G)
        print('prior to merging, the max cut value of',key,'is', unaltered_cut_value)
        
        # Merge: merge the results from the conquer stage
        print('Merging these solutions together for a solution to',key)
        # Define the border graph
        bordergraph = border(G, subgraph_dictionary)
        # Define the merger graph
        merger_graph = createMergerGraph(bordergraph, subgraph_dictionary)
       
        try:
            # Apply QAOA to the merger graph
            merger_results = merging(G, subgraph_dictionary, merger_graph)
        except: 
            # In case QAOA for merger graph does not converge, don't flip any of the colors for the merger
            mergerResultsList = [0]*nx.number_of_nodes(merger_graph)
            merger_results = ''.join(str(x) for x in mergerResultsList)
            print('Merging subroutine opted out with an error for', key)
        
        # Color the nodes of G to indicate the merged subgraph solutions
        alteredG, new_color_list = new_colors(subgraph_dictionary, G, merger_graph, merger_results)
        newcut = cutvalue(alteredG)
        print('the merger algorithm produced a new coloring of',key,'with cut value,',newcut)

        
        
        return new_color_list
##################################################################################
# end of definitions
# beginning of algorithm
##################################################################################
if rank ==0:
    # Load graph
    # Use the graph from Lab 3 to test out the algorithm
    
    # Newman Watts Strogatz network model
    #n = 100 # number of nodes
    #k = 4 # each node joined to k nearest neighbors
    #p =0.8 # probability of adding a new edge
    #seed = 1234
    #sampleGraph3=nx.newman_watts_strogatz_graph(n, k, p, seed=seed)


    # Random d-regular graphs used in the paper arxiv:2205.11762
    # d from 3, 9 inclusive
    # number of vertices from from 60 to 80
    # taking d=6 and n =100, works well
    d = 6
    n =70
    graph_seed = 1234
    sampleGraph3=nx.random_regular_graph(d,n,seed=graph_seed)

    #random graph from lab 2 
    #n = 30  # number of nodes
    #m = 70  # number of edges
    #seed= 20160  # seed random number generators for reproducibility
    # Use seed for reproducibility
    #sampleGraph3= nx.gnm_random_graph(n, m, seed=seed)
    
    # set edge weights equal to 1
    # all weights = 1 is equivalent to solving the unweighted max cut problem
    nx.set_edge_attributes(sampleGraph3, values = 1, name = 'weight')
    
    # set edge weights of -1 and 1 from a non uniform distribution
    #np.random.seed(seed)
    #for e in sampleGraph3.edges():
    #    random_assignment = np.random.randint(0, 1)
    #    sampleGraph3.edges[e]['weight'] = -1**random_assignment
    
    # set edge weights of 0 and 5 from a non uniform distribution
    #np.random.seed(seed)
    #for e in sampleGraph3.edges():
    #    random_assignment = np.random.randint(0, 5)
    #    sampleGraph3.edges[e]['weight'] = random_assignment
    
    
    # subdivide once
    def Lab2SubgraphPartition(G,n):
        """Divide the graph up into at most n subgraphs
    
        Parameters
        ----------
        G: networkX.Graph 
            Graph that we want to subdivide
        n : int
            n is the maximum number of subgraphs in the partition

        Returns
        -------
        dict of str : networkX.Graph
            Dictionary of networkX graphs with a string as the key
        """
        # n is the maximum number of subgraphs in the partition
        greedy_partition = community.greedy_modularity_communities(G, weight=None, resolution=1.1, cutoff=1, best_n=n)
        number_of_subgraphs = len(greedy_partition)

        graph_dictionary = {}
        graph_names=[]
        for i in range(number_of_subgraphs):
            name='Global:'+str(i)
            graph_names.append(name)

        for i in range(number_of_subgraphs):
            nodelist = sorted(list(greedy_partition[i]))
            graph_dictionary[graph_names[i]] = nx.subgraph(G, nodelist)
     
        return(graph_dictionary) 

    subgraph_dictionary = Lab2SubgraphPartition(sampleGraph3,12)
    
    # Assign the subgraphs to the QPUs
    number_of_subgraphs = len(sorted(subgraph_dictionary))
    number_of_subgraphs_per_qpu = int(np.ceil(number_of_subgraphs/num_qpus))

    keys_on_qpu ={}
    
    for q in range(num_qpus):
        keys_on_qpu[q]=[]
        for k in range(number_of_subgraphs_per_qpu):
            if (k*num_qpus+q < number_of_subgraphs):
                key = sorted(subgraph_dictionary)[k*num_qpus+q]
                keys_on_qpu[q].append(key)        
    print('Subgraph problems to be computed on each processor have been assigned')
    # Allocate subgraph problems to the GPUs
    # Distribute the subgraph data to the QPUs
    for i in range(num_qpus):
        subgraph_to_qpu ={}
        for k in keys_on_qpu[i]:
            subgraph_to_qpu[k]= subgraph_dictionary[k]
        if i != 0:
            comm.send(subgraph_to_qpu, dest=i, tag=rank)
        else:
            assigned_subgraph_dictionary = subgraph_to_qpu
else:
# Receive the subgraph data
    assigned_subgraph_dictionary= comm.recv(source=0, tag=0)
    print("Processor {} received {} from processor {}".format(rank,assigned_subgraph_dictionary, 0))


#########################################################################
# Recursively solve subgraph problems assigned to GPU
# and return results back to GPU0 for final merger
#########################################################################
num_subgraphs=11 # limits the size of the merger graphs
num_qubits = 14 # max number of qubits allowed in a quantum circuit
layer_count =1 # Layer count for the QAOA max cut # Edit this line to change the layer count
seed = 13 # Seed for QAOA for max cut  # Edit this line to change the seed for the random initial parameters
results = {}
for key in assigned_subgraph_dictionary:
    G = assigned_subgraph_dictionary[key]
    newcoloring_of_G = subgraph_solution(G, key, num_subgraphs, num_qubits, layer_count, G, seed = seed)
    results[key]=newcoloring_of_G


############################################################################
# Copy over the subgraph solutions from the individual GPUs
# back to GPU 0.
 #############################################################################
# Copy the results over to QPU 0 for consolidation 
if rank!=0:
    comm.send(results, dest=0, tag = 0)
    print("{} sent by processor {}".format(results, rank))
    
else:
    for j in range(1,num_qpus,1):
        colors  = comm.recv(source = j, tag =0)
        print("Received {} from processor {}".format(colors, j))
        for key in colors:
            results[key]=colors[key]
    print("The results dictionary on GPU 0 =", results)
 
    
    #######################################################
    # Step 3
    ####################################################### 
    ############################################################################
    # Merge results on QPU 0
    ############################################################################  
    
    # Add color attribute to subgraphs and sampleGraph3 to record the subgraph solutions
    
    subgraphColors={}

    for key in subgraph_dictionary:
        subgraphColors[key]=[int(i) for i in results[key]]

    for key in subgraph_dictionary:
        G = subgraph_dictionary[key]
        for v in sorted(list(nx.nodes(G))):
            G.nodes[v]['color']=subgraphColors[key][sorted(list(nx.nodes(G))).index(v)]
            sampleGraph3.nodes[v]['color']=G.nodes[v]['color']
    
    

    
    print('The divide-and-conquer QAOA unaltered cut approximation of the graph, prior to the final merge, is ',cutvalue(sampleGraph3))
    
    # Merge
    borderGraph = border(sampleGraph3, subgraph_dictionary)
    mergerGraph = createMergerGraph(borderGraph, subgraph_dictionary)
    merger_results = merging(sampleGraph3, subgraph_dictionary, mergerGraph)
    maxcutSampleGraph3, G_colors_with_maxcut = new_colors(subgraph_dictionary, sampleGraph3, mergerGraph, merger_results)
    
   

    
    print('The divide-and-conquer QAOA max cut approximation of the graph is ',cutvalue(maxcutSampleGraph3))
    
    ###### can parallelize this
    number_of_approx =10
    randomlist = np.random.choice(3000,number_of_approx)
    minapprox = nx.algorithms.approximation.one_exchange(sampleGraph3, initial_cut=None, seed=int(randomlist[0]))[0]
    maxapprox = minapprox
    sum_of_approximations = 0
    for i in range(number_of_approx):
        seed = int(randomlist[i])
        ith_approximation = nx.algorithms.approximation.one_exchange(sampleGraph3, initial_cut=None, seed=seed)[0]
        if ith_approximation < minapprox:
            minapprox = ith_approximation
        if ith_approximation > maxapprox:
            maxapprox = ith_approximation
        sum_of_approximations +=ith_approximation

    average_approx = sum_of_approximations/number_of_approx

    print('This compares to a few runs of the greedy modularity maximization algorithm gives an average approximate Max Cut value of',average_approx)
    print('with approximations ranging from',minapprox,'to',maxapprox)