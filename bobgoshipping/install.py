from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from bobgoshipping.custom_fields import get_custom_fields
from bobgoshipping.property_setters import get_property_setters
from bobgoshipping.utils import make_property_setters


def after_install():
	create_custom_fields(get_custom_fields())
	make_property_setters(get_property_setters())
