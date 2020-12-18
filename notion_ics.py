
import json
import datetime
from icalendar import Calendar, Event
from notion.client import NotionClient
from notion.collection import CalendarView
from notion.block import BasicBlock
from notion.user import User


# Hack some representation stuff into notion-py

BasicBlock.__repr__ = BasicBlock.__str__ = lambda self: self.title
User.__repr__ = User.__str__ = lambda self: self.given_name or self.family_name


def get_ical(client, calendar_url, title_format, calendar_by=None, debug=False):
    
    # Retrieve information from Notion with any views
    calendar = client.get_block(calendar_url).views[0]
    collection = calendar.collection
    schema = collection.get_schema_properties()
    calendar_entries = calendar.build_query().execute()

    # Collate schema info
    properties_by_name = {}
    properties_by_slug = {}
    properties_by_id = {}
    title_prop = None
    calendar_by_list=[]

    for prop in schema:
        name = prop['name']
        if name in properties_by_name:
            print("WARNING: duplicate property with name {}".format(name))
        properties_by_name[name] = prop
        properties_by_slug[prop['slug']] = prop
        properties_by_id[prop['id']] = prop
        if prop['type'] == 'title':
            title_prop = prop
        if prop['type'] == 'date':
            calendar_by_list.append(prop)
            
    assert title_prop is not None, "Couldn't find a title property"
    assert len(calendar_by_list) > 0, "Table without a date property"

    if calendar_by is not None and calendar_by != "": 
        dateprop = properties_by_slug[calendar_by]
    else:
        dateprop = properties_by_id[calendar_by_list[0]["id"]]

    cal = Calendar()
    cal.add("summary", "Imported from Notion, via notion-export-ics.")
    cal.add('version', '2.0')
    
    for e in calendar_entries:
        date = e.get_property(dateprop['id'])
        if date is None:
            continue
        
        name = e.get_property(title_prop['id'])
        clean_props = {'NAME': name}
        
        # Put in ICS file
        event = Event()
        desc = ''
        event.add('dtstart', date.start)
        if date.end is not None:
            if not isinstance(end, datetime.datetime):
                date.end += datetime.timedelta(days=(1))
            event.add('dtend', date.end)
        else:
            date.end = date.start + datetime.timedelta(hours=(1))

        desc += e.get_browseable_url() + '\n\n'
        desc += 'Properties:\n'
        for k, v in e.get_all_properties().items():
            if k != dateprop['slug']:
                name = properties_by_slug[k]['name']
                desc += "  - {}: {}\n".format(name, v)
                clean_props[name] = v
        title = title_format.format_map(clean_props)
        event.add('summary', title)
        event.add('description', desc)
        cal.add_component(event)
        
        # Print
        if debug:
            print("{}: {} -> {}".format(title, date.start, date.end))
            print(desc)
            print('--------------')
    
    return cal
