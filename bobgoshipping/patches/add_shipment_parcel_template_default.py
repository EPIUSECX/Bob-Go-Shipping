from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from bobgoshipping.custom_fields import get_fields_for_patch


def execute():
	create_custom_fields(get_fields_for_patch("Shipment Parcel Template", ["is_default"]))
