"""Reads the database and delivers reminders."""

import datetime
import json
import pywikibot
import sys

BOT_NAME = "RemindMeBot"
TIME_RESOLUTION = datetime.timedelta(minutes=30)
REMINDERS_FILE = "reminders.json"
SUMMARY = "Bot delivering a reminder about [[{0}]]"

def round_time(some_time):
    some_time = some_time + TIME_RESOLUTION
    return some_time.replace(second=0, minute=0)

def check_reminder_time(reminder):
    """Returns true if the reminder can be sent now."""
    reminder_timestamp = reminder[3]
    rounded_now = round_time(datetime.datetime.utcnow())
    return reminder_timestamp == rounded_now

def send_reminder(site, reminder):
    username, location, notification_timestamp, reminder_time, note = reminder
    user_talk_page = pywikibot.Page(site, "User talk:" + username)
    template = ("{{User:" + BOT_NAME + "/template|time=" +
                notification_timestamp + "|page=" + location + "|text=" + note +
                "}}")
    user_talk_page.text += "\n\n" + template
    user_talk_page.save(summary=SUMMARY.format(location))

def main():
    print("Starting {}-write at {}".format(BOT_NAME,
                                           datetime.datetime.utcnow().isoformat()))

    site = pywikibot.Site("en", "wikipedia")
    site.login()
    current_user = site.user()
    if current_user != BOT_NAME:
        print("Error! Logged in as {} instead of {}.".format(current_user, BOT_NAME))
        sys.exit(1)
    else:
        print("Logged in as {}.".format(current_user))

    reminders = []
    with open(REMINDERS_FILE, "r") as reminders_file:
        reminders = json.load(reminders_file)

    sendable_reminders = filter(check_reminder_time, reminders)
    if len(sendable_reminders) == 0:
        print("No sendable reminders, exiting")
        sys.exit(0)

    for reminder in sendable_reminders:
        send_reminder(site, reminder)

if __name__ == "__main__":
    main()
