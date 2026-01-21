import networkx as nx


def build_random_gas_network() -> nx.DiGraph:
	"""Build a fixed example gas network with edge and node capacities.
	Nodes have attributes:
	- kind: "source" | "sink" | "intermediate"
	- node_capacity: max total flow through the node
	- demand (sinks only): desired gas amount

	Edges have attribute:
	- capacity: max flow on the edge
	"""

	G = nx.DiGraph()

	G.add_node("src_0", kind="source", node_capacity=12_000)
	G.add_node("src_1", kind="source", node_capacity=10_000)

	G.add_node("mid_0", kind="intermediate", node_capacity=9_000)
	G.add_node("mid_1", kind="intermediate", node_capacity=9_000)
	G.add_node("mid_2", kind="intermediate", node_capacity=9_000)

	G.add_node("sink_0", kind="sink", node_capacity=7_000, demand=6_000)
	G.add_node("sink_1", kind="sink", node_capacity=8_000, demand=7_000)
	G.add_node("sink_2", kind="sink", node_capacity=8_000, demand=5_000)

	G.add_edge("src_0", "mid_0", capacity=8_000)
	G.add_edge("src_0", "mid_1", capacity=6_000)
	G.add_edge("src_1", "mid_1", capacity=5_000)
	G.add_edge("src_1", "mid_2", capacity=7_000)

	G.add_edge("mid_0", "mid_2", capacity=4_000)
	G.add_edge("mid_0", "sink_0", capacity=5_000)

	G.add_edge("mid_1", "sink_0", capacity=3_000)
	G.add_edge("mid_1", "sink_1", capacity=6_000)

	G.add_edge("mid_2", "sink_1", capacity=4_000)
	G.add_edge("mid_2", "sink_2", capacity=8_000)

	return G


def build_flow_network_with_node_capacities(base_graph: nx.DiGraph) -> nx.DiGraph:
	"""Transform node-capacity network into an edge-capacity flow network.

	Each original node v is split into v_in -> v_out with capacity=node_capacity[v].
	Original edges (u, v) become (u_out, v_in) with the same capacity.
	A super source connects to all sources, and sinks connect to a super sink with
	capacity equal to their demand.
	"""

	F = nx.DiGraph()

	super_source = "super_source"
	super_sink = "super_sink"
	F.add_node(super_source)
	F.add_node(super_sink)

	for n, data in base_graph.nodes(data=True):
		node_cap = data.get("node_capacity")
		if node_cap is None:
			raise ValueError(f"Node {n} missing node_capacity")

		n_in = f"{n}_in"
		n_out = f"{n}_out"
		F.add_node(n_in, original=n, role="in")
		F.add_node(n_out, original=n, role="out")
		F.add_edge(n_in, n_out, capacity=node_cap)

	for u, v, data in base_graph.edges(data=True):
		cap = data.get("capacity")
		if cap is None:
			raise ValueError(f"Edge ({u}, {v}) missing capacity")
		F.add_edge(f"{u}_out", f"{v}_in", capacity=cap)

	for n, data in base_graph.nodes(data=True):
		kind = data.get("kind")
		if kind == "source":
			F.add_edge(super_source, f"{n}_in", capacity=10**12)

	for n, data in base_graph.nodes(data=True):
		kind = data.get("kind")
		if kind == "sink":
			demand = data.get("demand")
			if demand is None:
				raise ValueError(f"Sink node {n} missing demand")
			F.add_edge(f"{n}_out", super_sink, capacity=demand)

	return F


def run_gas_flow_demo() -> None:
	base = build_random_gas_network()
	flow_graph = build_flow_network_with_node_capacities(base)

	super_source = "super_source"
	super_sink = "super_sink"

	flow_value, flow_dict = nx.maximum_flow(
		flow_graph, super_source, super_sink, capacity="capacity"
	)

	sinks: list[str] = [
		n for n, data in base.nodes(data=True) if data.get("kind") == "sink"
	]

	print("=== Gas Network Flow Demo ===")
	print(f"Total max flow delivered to sinks: {int(flow_value):,}")

	total_demand = 0
	total_delivered = 0

	for sink in sinks:
		demand = int(base.nodes[sink]["demand"])
		delivered = int(flow_dict.get(f"{sink}_out", {}).get(super_sink, 0))
		total_demand += demand
		total_delivered += delivered
		print(
			f"Sink {sink}: demand={demand:,}  delivered={delivered:,}  "
			f"shortfall={max(0, demand - delivered):,}"
		)

	print("---")
	print(f"Total demand across sinks: {total_demand:,}")
	print(f"Total delivered to sinks: {total_delivered:,}")

	print("\nNode capacities:")
	for n, data in base.nodes(data=True):
		print(
			f"  {n:8s} kind={data.get('kind'):12s} "
			f"node_capacity={int(data['node_capacity']):,}"
		)

	visualize_network_and_flow(base, flow_dict)


def visualize_network_and_flow(base_graph: nx.DiGraph, flow_dict: dict) -> None:
	"""Visualize the base gas network and the max-flow solution.

	Edges are labeled with "flow/capacity" on the original network.
	"""

	try:
		import matplotlib.pyplot as plt  # type: ignore[import]
	except ImportError:
		print("matplotlib not installed; skipping visualization.")
		return

	pos = nx.spring_layout(base_graph, seed=7)

	kind_attr = nx.get_node_attributes(base_graph, "kind")
	node_colors: list[str] = []
	for n in base_graph.nodes:
		kind = kind_attr.get(n)
		if kind == "source":
			color = "lightgreen"
		elif kind == "sink":
			color = "salmon"
		else:
			color = "lightblue"
		node_colors.append(color)

	edge_capacities = nx.get_edge_attributes(base_graph, "capacity")
	edge_flows: dict[tuple[str, str], float] = {}
	for u, v in base_graph.edges:
		flow_uv = float(flow_dict.get(f"{u}_out", {}).get(f"{v}_in", 0.0))
		edge_flows[(u, v)] = flow_uv

	plt.figure(figsize=(8, 6))
	nx.draw_networkx_nodes(base_graph, pos, node_color=node_colors, edgecolors="black")
	nx.draw_networkx_edges(base_graph, pos, arrowstyle="->", arrowsize=15)
	nx.draw_networkx_labels(base_graph, pos, font_size=9)

	edge_labels = {}
	for (u, v), cap in edge_capacities.items():
		flow_uv = edge_flows.get((u, v), 0.0)
		edge_labels[(u, v)] = f"{int(flow_uv)}/{int(cap)}"

	nx.draw_networkx_edge_labels(
		base_graph,
		pos,
		edge_labels=edge_labels,
		font_size=8,
		label_pos=0.5,
	)

	# Draw self-loop edges to represent in/out node-capacity edges (n_in -> n_out)
	self_edges = []
	self_edge_labels = {}
	for n in base_graph.nodes:
		node_cap = base_graph.nodes[n].get("node_capacity")
		if node_cap is None:
			continue
		node_flow = float(flow_dict.get(f"{n}_in", {}).get(f"{n}_out", 0.0))
		self_edges.append((n, n))
		self_edge_labels[(n, n)] = f"{int(node_flow)}/{int(node_cap)}"

	if self_edges:
		nx.draw_networkx_edges(
			base_graph,
			pos,
			edgelist=self_edges,
			arrowstyle="-|>",
			arrowsize=12,
			edge_color="gray",
			style="dashed",
			connectionstyle="arc3,rad=0.3",
		)
		nx.draw_networkx_edge_labels(
			base_graph,
			pos,
			edge_labels=self_edge_labels,
			font_size=7,
			label_pos=0.2,
		)

	plt.title("Gas network (edge and node flow/capacity)")
	plt.axis("off")
	plt.tight_layout()
	plt.show()


if __name__ == "__main__":
	run_gas_flow_demo()


