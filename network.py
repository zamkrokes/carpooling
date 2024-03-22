import osmnx as osm
import networkx as nx

area = 'Maxvorstadt, Munich, Germany'

network_selected_drive = osm.graph_from_place(area, network_type='drive')
network_selected_walk = osm.graph_from_place(area, network_type='walk')

projected_network_selected = osm.project_graph(network_selected_drive)
clean_network_selected = osm.consolidate_intersections(projected_network_selected, rebuild_graph=True, tolerance = 10, dead_ends=False)
network_drive = clean_network_selected
network_drive = osm.add_edge_speeds(network_drive)
network_drive = osm.add_edge_travel_times(network_drive)

projected_network_selected_walk = osm.project_graph(network_selected_walk)
clean_network_selected_walk = osm.consolidate_intersections(projected_network_selected_walk, rebuild_graph=True, tolerance = 5, dead_ends=False)
network_walk = clean_network_selected_walk
network_walk = osm.add_edge_speeds(network_walk)
network_walk = osm.add_edge_travel_times(network_walk)

network_drive_nodes = osm.graph_to_gdfs(network_drive, nodes=True, edges=False)
network_walk_nodes = osm.graph_to_gdfs(network_walk, nodes=True, edges=False)

# combine the two networks
network_combined = nx.compose(projected_network_selected_walk, projected_network_selected)
clean_network_combined = osm.consolidate_intersections(network_combined, rebuild_graph=True, tolerance = 5, dead_ends=False)
network_combined = clean_network_combined
network_combined = osm.add_edge_speeds(network_combined)
network_combined = osm.add_edge_travel_times(network_combined)

network_nodes = osm.graph_to_gdfs(network_combined, nodes=True, edges=False)