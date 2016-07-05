"""Reads my notifications and writes new reminders to the database."""

import datetime
import json
import mwparserfromhell
import pytimeparse
import pywikibot
import re
import sys

BOT_NAME = "RemindMeBot"
SIGNATURE_TIMESTAMP_FORMAT = "%H:%M, %-d %B %Y"
INITIAL_INDENTATION = re.compile("^[*: ]+")
BEFORE_PING = re.compile(r".+ ([[(User:)?{0}(|.*)?]]|\{{\{{\w+\|{0}\}}\}})".format(BOT_NAME))
SIGNATURE_REGEX = r"\[\[User.*?:{}.+\(UTC\)"
LEAD_TRAIL_PUNCT = re.compile(r"^[^\w\d]*(.+?)[^\w\d]*$")
TIME_RESOLUTION = datetime.timedelta(minutes=30)
REMINDERS_FILE = "reminders.json"

def parse_duration(input_string):
    """Wrapper around pytimeparse to parse a time duration and return a
    regular timedelta"""
    return datetime.timedelta(seconds=pytimeparse.parse(input_string))

def parse_line(line, username):
    """
    Parses a line with a comment (given the username of the user who made it)
    and returns a time duration and a note.
    """
    line = INITIAL_INDENTATION.sub("", line)

    # Remove everything before and including the ping
    line = BEFORE_PING.sub("", line)

    # Remove the signature and everything after it
    line = re.sub(SIGNATURE_REGEX.format(username), "", line)

    # Remove leading and trailing punctuation
    line = LEAD_TRAIL_PUNCT.sub(r"\1", line)
    time_duration, _, note = line.partition(",")
    return (time_duration, note.strip())

class SectionIdentifier:
    """Identifies which section a line came from."""
    def __init__(self, page_content):
        wikicode = mwparserfromhell.parse(page_content)
        self.sections = []
        for each_section in wikicode.get_sections()[1:]:
            first_heading = each_section.filter_headings()[0]
            title = first_heading.title.strip()
            each_section.remove(first_heading)
            text = unicode(each_section).strip()
            self.sections.append((title, text))

    def lookup(self, text):
        try:
            return next(x[0] for x in self.sections if text in x[1])
        except StopIteration:
            return None

def main():
    print("Starting {} at {}".format(BOT_NAME,
                                     datetime.datetime.utcnow().isoformat()))

    site = pywikibot.Site("en", "wikipedia")
    site.login()
    current_user = site.user()
    if current_user != BOT_NAME:
        print("Error! Logged in as {} instead of {}.".format(current_user, BOT_NAME))
        sys.exit(1)
    else:
        print("Logged in as {}.".format(current_user))

    # Read through my notifications and get a list of new reminders to send
    new_reminders = []
    for notification in site.notifications():
        if notification.type != "mention": continue
        username = notification.agent.username

        page_content = notification.page.getOldVersion(notification.revid)
        section_identifier = SectionIdentifier(page_content)
        line_parts = [current_user, username,
                      notification.timestamp.strftime(SIGNATURE_TIMESTAMP_FORMAT)]
        has_line_parts = lambda line: all(x in line for x in line_parts)
        for each_line in filter(has_line_parts, page_content.splitlines()):
            print("In inner loop")
            time_duration, note = parse_line(each_line, username)

            time_duration = parse_duration(time_duration)
            reminder_time = notification.timestamp + time_duration
            reminder_time = TIME_RESOLUTION + reminder_time
            reminder_time = reminder_time.replace(second=0, minute=0)

            # We can't send reminders in the past
            if reminder_time < datetime.datetime.now(): continue

            location = u"%s#%s" % (notification.page.title(withNamespace=True),
                                  section_identifier.lookup(each_line))

            reminder = (username, location, notification.timestamp, reminder_time, note)
            new_reminders.append(reminder)

    with open(REMINDERS_FILE, "w") as reminders_file:
        json.dump(new_reminders, reminders_file)
        print("Wrote {} new reminders to {}.".format(len(new_reminders), REMINDERS_FILE))

if __name__ == "__main__":
    main()
