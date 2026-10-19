from django import template
from governance.capabilities import allows

register = template.Library()
register.filter("cap", allows)
