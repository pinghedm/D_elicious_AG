import json
from collections import defaultdict

import graphviz as gv
import yaml


class Node:
	def __init__(self, slug_name, display_name, node_type):
		self.slug_name = slug_name
		self.display_name = display_name
		self.children = []
		self.node_type = node_type

	def produce_graph_node(self, graph):
		if self.node_type == 'ingredient':
			shape = 'diamond'
		elif self.node_type == 'start':
			shape = 'Mdiamond'
		else:
			shape = 'oval'
		return graph.node(self.slug_name, self.display_name, shape = shape)


def slugify(name):
	return name.lower().replace(' ', '-')

sample_recipe = '../data/maple_glazed_water_challah.recipe'
with open(sample_recipe) as f:
	recipe_structure = yaml.safe_load(f)


root_node = Node('start', 'start', 'start')
nodes_by_slug = {'start': root_node}




flattened_ingredients = {}
for ing_key, ing_vals in recipe_structure['ingredients'].items():
	for ingredient_obj in ing_vals:
		for ing_name, ing_amounts in ingredient_obj.items():
			flattened_ingredients[ing_name] = ing_amounts
			node_val = f'{ing_name}: {ing_amounts["amount"]}'
			node_slug = slugify(ing_name)
			node = Node(node_slug, node_val, 'ingredient')
			root_node.children.append(node)
			nodes_by_slug[node_slug] = node


step_deps_by_step = defaultdict(set)
first_do_by_step_name = {}
last_do_by_step_name = {}

for idx, step in enumerate(recipe_structure['steps']):
	step_name = step['name']
	step_slug = slugify(step['name'])
	ing_dep = step['ing_dep']
	step_dep = step['step_dep']

	do_slugs = [json.dumps(do) for do in step['do']]
	do_nodes = []
	for do in do_slugs:
		print(do)
		new_node = Node(do, step_name + do, 'step')
		do_nodes.append(new_node)
		nodes_by_slug[do] = do
	for pair in zip(do_nodes, do_nodes[1:]):
		pair[0].children.append(pair[1])

	first_do_by_step_name[step_slug] = do_nodes[0]
	last_do_by_step_name[step_slug] = do_nodes[-1]

	if ing_dep:
		ing_dep_nodes = []
		for ing_obj in ing_dep:
			ing_slug = slugify(ing_obj['name'])
			ing_dep_nodes.append(nodes_by_slug[ing_slug])

		for dep in ing_dep_nodes:
			dep.children.append(do_nodes[0])

	if step_dep:
		step_dep_slugs = []

		if type(step_dep) == str:
			step_dep_slugs.append(slugify(step_dep))
		elif type(step_dep) == list:
			for dep in step_dep:
				step_dep_slugs.append(slugify(dep))

		step_deps_by_step[step_slug] = set(step_dep_slugs)


	if step_dep is None:# and ing_dep is None:
		root_node.children.append(do_nodes[0])


for step_slug, step_dep_slugs in step_deps_by_step.items():
	first_do_node = first_do_by_step_name[step_slug]
	for dep in step_dep_slugs:
		last_do_node = last_do_by_step_name[dep]
		last_do_node.children.append(first_do_node)


def walk(root, graph, edges):
	for child in root.children:
		child.produce_graph_node(graph)
		if not (root.slug_name != 'start' or child.node_type != 'ingredient'):
			pass
		else:
			edges.add((root.slug_name, child.slug_name))
		edges = walk(child, graph, edges)
	return edges


if __name__ == '__main__':
	print('--------------------------------')
	print(root_node.display_name)

	graph = gv.Digraph(format = 'png')
	graph.attr(splines = 'false')
	root_node.produce_graph_node(graph)
	edges = set()

	edges = walk(root_node, graph, edges)
	for edge in edges:
		graph.edge(*edge)

	graph.render('/tmp/recipe')
