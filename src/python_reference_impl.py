from collections import defaultdict
from pprint import pprint

import graphviz as gv
import yaml


class InvalidDAGException(Exception):
	pass

def slugify(name):
	return name.lower().replace(' ', '-')


class DAG:
	def __init__(
		self,
		nodes_by_slug = None,
		edges = None,
		graph = None,
	):
		if nodes_by_slug is None:
			self.make_start_node()
			nodes_by_slug = {
				self.start_node.slug_name: self.start_node,
			}
		self.nodes_by_slug = nodes_by_slug

		if edges is None:
			edges = set()
		self.edges = set(edges)

		if graph is None:
			graph = gv.Digraph(format = 'png')
			graph.attr(splines = 'false')
		self.graph = graph

		self._adjacency_list = {}

	def make_start_node(self):
		self.start_node = Node('start', 'start', 'start')

	def _get_key(self, node_or_slug):
		if type(node_or_slug) == Node:
			return node_or_slug.slug_name
		return node_or_slug


	def add_edge(self, from_node_or_slug, to_node_or_slug):
		from_key = self._get_key(from_node_or_slug)
		to_key = self._get_key(to_node_or_slug)
		self.edges.add((from_key, to_key))
		self._adjacency_list = {}

	def validate(self):
		errors = []
		# for every side of an edge, we must have a node with that slug
		for from_, to in self.edges:
			if from_ not in self.nodes_by_slug:
				errors.append(f'Not found: {from_}')
			if to not in self.nodes_by_slug:
				errors.append(f'Not found: {to}')
		if errors:
			raise InvalidDAGException('\n' + '\n'.join(errors))

		# To come - validate no cycles?

	@property
	def adjacency_list(self):
		if self._adjacency_list:
			return self._adjacency_list
		adj_list = defaultdict(set)
		for from_key, to_key in self.edges:
			adj_list[from_key].add(to_key)
		self._adjacency_list = dict(adj_list)
		return self._adjacency_list


	def _topological_sort(self, node, reverse_node_list):
		node.visited = True
		for adjacent_node_slug in self.adjacency_list.get(node.slug_name, []):
			adjacent_node = self.nodes_by_slug[adjacent_node_slug]
			if adjacent_node and not adjacent_node.visited:
				self._topological_sort(adjacent_node, reverse_node_list)
		reverse_node_list.append(node)

	def topological_sort(self):
		reverse_node_list = []
		for node in self.nodes_by_slug.values(): node.visited = False
		for node in self.nodes_by_slug.values():
			if not node.visited:
				self._topological_sort(node, reverse_node_list)
		for node in self.nodes_by_slug.values(): node.visited = False
		return reverse_node_list[::-1]

	def produce_image(self, filename = None):
		self.validate()
		for node in self.nodes_by_slug.values():
			node.produce_graph_node(self.graph)
		for from_key, to_key in self.edges:
			from_node = self.nodes_by_slug[from_key]
			to_node = self.nodes_by_slug[to_key]
			if not (from_node.node_type == 'start' and to_node.node_type == 'ingredient'):
				self.graph.edge(from_key, to_key)

		if filename:
			self.graph.render(filename)

class Node:
	shape_by_node_type = {
		'ingredient': 'diamond',
		'start': 'Mdiamond',
	}

	def __init__(
		self,
		slug_name,
		display_name,
		node_type = 'step',
	):
		self.slug_name = slug_name
		self.display_name = display_name
		self.node_type = node_type
		self.visited = False

	def __str__(self):
		return self.display_name
	def __repr__(self):
		return f'Node({self.slug_name}, {self.display_name}, {self.node_type})'

	def produce_graph_node(self, graph):
		shape = self.shape_by_node_type.get(
			self.node_type,
			'oval',
		)
		return graph.node(
			self.slug_name,
			self.display_name,
			shape = shape,
		)


sample_recipe = '../data/maple_glazed_water_challah.recipe'
with open(sample_recipe) as f:
	recipe_structure = yaml.safe_load(f)

graph = DAG()

ingredient_nodes_by_slug_name = {}
for recipe_group, ingredients in recipe_structure['ingredients'].items():
	for ingredient in ingredients:
		for ingredient_name, ingredient_data in ingredient.items():
			node_display_name = f'Measure out {ingredient_data["amount"]} of {ingredient_name}'
			node_slug_name = slugify(ingredient_name)
			node = Node(
				node_slug_name,
				node_display_name,
				node_type = 'ingredient',
			)
			graph.nodes_by_slug[node_slug_name] = node
			graph.add_edge(graph.start_node, node)

step_dependency_slugs_by_step_slug = {}
first_substep_slug_by_step_slug = {}
last_substep_slug_by_step_slug = {}

for step in recipe_structure['steps']:
	step_name = step['name']
	step_slug = slugify(step['name'])
	ingredients = step['ing_dep']
	step_dependencies = step['step_dep']

	substeps = step['do']
	substep_slugs = []
	for idx, substep in enumerate(substeps, start = 1):
		substep_slug = slugify(substep)
		substep_slugs.append(substep_slug)
		new_node = Node(
			substep_slug,
			f'({step_name} - {idx}/{len(substeps)}) {substep}',
		)
		graph.nodes_by_slug[substep_slug] = new_node

	for earlier_step, later_step in zip(substep_slugs, substep_slugs[1:]):
		graph.add_edge(earlier_step, later_step)

	first_substep_slug = substep_slugs[0]
	last_substep_slug = substep_slugs[-1]
	first_substep_slug_by_step_slug[step_slug] = first_substep_slug
	last_substep_slug_by_step_slug[step_slug] = last_substep_slug

	if ingredients:
		ingredient_dependencies = []
		for ingredient in ingredients:
			ingredient_slug_name = slugify(ingredient['name'])
			ingredient_node = graph.nodes_by_slug[ingredient_slug_name]
			graph.add_edge(ingredient_node, first_substep_slug)

	if step_dependencies:
		step_dependency_slug_names = []

		if type(step_dependencies) == str:
			step_dependency_slug_names.append(slugify(step_dependencies))
		elif type(step_dependencies) == list:
			for step_dep in step_dependencies:
				step_dependency_slug_names.append(slugify(step_dep))

		step_dependency_slugs_by_step_slug[step_slug] = step_dependency_slug_names
	else:
		graph.add_edge(graph.start_node, first_substep_slug)


for step_slug, step_dep_slugs in step_dependency_slugs_by_step_slug.items():
	first_substep_slug = first_substep_slug_by_step_slug[step_slug]
	for dep_slug in step_dep_slugs:
		last_substep_node = last_substep_slug_by_step_slug[dep_slug]
		graph.add_edge(last_substep_node, first_substep_slug)

if __name__ == '__main__':

	graph.produce_image('/tmp/recipe')
	for idx, node in enumerate(graph.topological_sort(), start = 1):
		print(idx, node)
