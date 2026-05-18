# Copyright (c) 2020, Janlu Paulsen and Contributors
# See license.txt

# import frappe
import unittest

from bobgoshipping.bobgoshipping.utils import format_tracking_url_reference


class TestParcelService(unittest.TestCase):
	def test_format_tracking_url_reference_replaces_tracking_number_placeholder(self):
		url = "https://tracking.example/{{ tracking_number }}"

		self.assertEqual(
			format_tracking_url_reference(url, "ABC123"),
			"https://tracking.example/ABC123",
		)

	def test_format_tracking_url_reference_does_not_render_jinja_expressions(self):
		url = "https://tracking.example/{{ tracking_number }}?debug={{ 7 * 7 }}"

		self.assertEqual(
			format_tracking_url_reference(url, "ABC123"),
			"https://tracking.example/ABC123?debug={{ 7 * 7 }}",
		)
