# File: store/templatetags/custom_filter.py

from django import template
import datetime
from django.utils import timezone
from django.utils.timesince import timesince as django_timesince

register = template.Library()


@register.filter(name='currency')
def currency(number):
    try:
        return "₹ " + str(number)
    except (TypeError, ValueError):
        return "₹ 0"


@register.filter(name='multiply')
def multiply(number, number1):
    try:
        return number * number1
    except (TypeError, ValueError):
        return 0


@register.filter(name='timesince_days')
def timesince_days(value):
    """Return number of days since the datetime"""
    if not value:
        return 0

    try:
        # Handle different types of datetime objects
        if hasattr(value, 'date'):
            # It's a datetime object
            if timezone.is_aware(value):
                now = timezone.now()
            else:
                now = timezone.make_aware(datetime.datetime.now())
                value = timezone.make_aware(value)
        else:
            # It might be a date object
            now = timezone.now().date()
            if hasattr(value, 'year'):
                # It's a date object
                pass
            else:
                return 0

        diff = now - value
        return diff.days if hasattr(diff, 'days') else 0
    except (TypeError, AttributeError):
        return 0


@register.filter(name='timesince')
def timesince_filter(value):
    """Custom timesince filter that handles None values and various datetime formats"""
    if not value:
        return 'Unknown time'

    try:
        # If it's already a datetime object, use it directly
        if isinstance(value, datetime.datetime):
            return django_timesince(value)

        # If it's a date object, convert to datetime
        if isinstance(value, datetime.date):
            # Convert date to datetime at midnight
            dt = datetime.datetime.combine(value, datetime.time.min)
            if timezone.is_aware(timezone.now()):
                dt = timezone.make_aware(dt)
            return django_timesince(dt)

        # If it's a string, try to parse it
        if isinstance(value, str):
            try:
                # Try parsing ISO format
                dt = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
                return django_timesince(dt)
            except ValueError:
                # Try other common formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y %H:%M:%S']:
                    try:
                        dt = datetime.datetime.strptime(value, fmt)
                        if timezone.is_aware(timezone.now()):
                            dt = timezone.make_aware(dt)
                        return django_timesince(dt)
                    except ValueError:
                        continue

        # If nothing worked, return the original Django timesince
        return django_timesince(value)

    except (TypeError, AttributeError, ValueError) as e:
        # Log the error for debugging
        print(f"Timesince filter error: {e}, value: {value}, type: {type(value)}")
        return 'Unknown time'


@register.filter(name='default_if_none')
def default_if_none(value, default):
    """Return default if value is None"""
    return default if value is None else value


@register.filter(name='stringformat')
def stringformat(value, fmt):
    """Format value using string formatting"""
    try:
        return fmt % value
    except (ValueError, TypeError):
        return value


@register.filter(name='add')
def add(value, arg):
    """Add the arg to the value"""
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        try:
            return value + arg
        except TypeError:
            return ''


@register.filter(name='pluralize')
def pluralize(value, suffix='s'):
    """Return a suffix if the value is not 1"""
    try:
        if int(value) != 1:
            return suffix
    except (ValueError, TypeError):
        pass
    return ''


@register.filter(name='slice')
def slice_filter(value, slices):
    """Return a slice of the list"""
    try:
        return value[slice(*[int(x) if x else None for x in slices.split(':')])]
    except (ValueError, TypeError, AttributeError):
        return value


@register.filter(name='yesno')
def yesno(value, arg="yes,no,maybe"):
    """Return yes/no/maybe based on truthiness"""
    try:
        bits = arg.split(',')
        if len(bits) < 2:
            return value

        yes, no, maybe = bits[0], bits[1], bits[2] if len(bits) >= 3 else bits[1]

        if value is None:
            return maybe
        if value:
            return yes
        return no
    except (ValueError, TypeError, AttributeError):
        return value


@register.filter(name='floatformat')
def floatformat(value, decimal_places=1):
    """Format float to specified decimal places"""
    try:
        if value is None:
            return ''
        float_val = float(value)
        return f"{float_val:.{int(decimal_places)}f}"
    except (ValueError, TypeError):
        return value


@register.filter(name='lower')
def lower(value):
    """Convert string to lowercase"""
    try:
        return str(value).lower()
    except (TypeError, AttributeError):
        return value


@register.filter(name='title')
def title(value):
    """Convert string to title case"""
    try:
        return str(value).title()
    except (TypeError, AttributeError):
        return value


@register.filter(name='truncatewords')
def truncatewords(value, arg):
    """Truncate after a certain number of words"""
    try:
        length = int(arg)
        words = str(value).split()
        if len(words) > length:
            return ' '.join(words[:length]) + '...'
        return value
    except (ValueError, TypeError, AttributeError):
        return value


@register.filter(name='length')
def length(value):
    """Return the length of the value"""
    try:
        return len(value)
    except TypeError:
        return 0


@register.filter(name='make_list')
def make_list(value):
    """Return the value turned into a list"""
    try:
        return list(str(value))
    except (TypeError, ValueError):
        return []


@register.filter(name='join')
def join(value, separator):
    """Join a list with a separator"""
    try:
        return separator.join(value)
    except (TypeError, AttributeError):
        return value


@register.filter(name='escape')
def escape_filter(value):
    """Escape HTML characters"""
    try:
        from django.utils.html import escape
        return escape(str(value))
    except (TypeError, AttributeError):
        return value


@register.filter(name='safe')
def safe_filter(value):
    """Mark a string as safe for HTML output"""
    try:
        from django.utils.safestring import mark_safe
        return mark_safe(value)
    except (TypeError, AttributeError):
        return value