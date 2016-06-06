#!/usr/bin/env python
#
# Copyright (c) 2016, PagerDuty, Inc. <info@pagerduty.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of PagerDuty Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL PAGERDUTY INC BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
import urllib2
import urllib
import json
import datetime
import pytz
from datetime import timedelta
from datetime import date
from collections import deque
import dateutil.parser

path = "https://api.pagerduty.com/"
WEEK = timedelta(days=7)
TIMEWINDOW = timedelta(days=180)
INDIE_ALERT_WINDOW = timedelta(minutes=30)

def run():
    parser = argparse.ArgumentParser(description='Graph alert volumes for a given escalation policy.')
    parser.add_argument('api_key', metavar='A', help='an API key for PagerDuty')
    parser.add_argument('-e', '--escalation_policy', nargs='?')

    args = parser.parse_args()
    api_key = args.api_key
    escalation_policy = args.escalation_policy

    if escalation_policy:
        services = get_services(api_key, escalation_policy)
        now = datetime.datetime.now(pytz.utc)

        incidents = get_incidents(api_key, services, date.today())
        deduped = dedup_incidents(incidents)
        print_volume_per_week(deduped, now - TIMEWINDOW)
    else:
        print_escalation_policies(api_key)

def print_volume_per_week(incident_times, start_time):
    current_count = 0

    end_window = start_time + WEEK
    for i in incident_times:
        if i < end_window:
            current_count += 1
        else:
            print "Week ending in %s: %d" % (str(end_window), current_count)
            current_count = 1
            end_window += WEEK
    print "Week ending in %s: %d" % (str(end_window), current_count)

def get_incidents(api_key, policy_id):
    services = get_services(api_key, policy_id)
    for s in services:
        (id, name) = (s.id, s.name)
        incidents = get_incidents(api_key, policy_id)

def print_escalation_policies(api_key):
    params = {
        "limit": 100
    }
    response = request("GET", "escalation_policies", api_key, params)
    data = json.loads(response)['escalation_policies']
    for e in data:
        print "%s %s" % (e['id'], e['name'])

def get_services(api_key, policy_id):
    entity = "escalation_policies/%s" % policy_id
    response = request("GET", entity, api_key)
    services = []
    j = json.loads(response)['escalation_policy']['services']
    for s in j:
        services.append(s['id'])
    return services

def get_incidents(api_key, services, end_time):
    service_str = list2csv(services)
    entity = "incidents"

    incidents = []
    more = True
    offset = 0
    limit = 100
    while (more):
        params = {
            "since": (end_time - TIMEWINDOW).isoformat(),
            "until": end_time.isoformat(),
            "offset": offset,
            "limit": 100,
            "service": service_str,
            "fields": "created_at"
        }
        response = request("GET", entity, api_key, params)
        incidents_json = json.loads(response)['incidents']
        for i in incidents_json:
            incidents.append(i['created_at'])
        offset += limit
        # If empty, stop
        more = incidents_json
    return incidents

def request(method, entity, token, params=None):
    headers = {
        "Content-type": "application/json",
        "Authorization": "Token token=%s" % token
    }
    url = path + entity
    if params:
        url = url + (("?%s") % urllib.urlencode(params))
    request = urllib2.Request(url, headers=headers)
    request.get_method = lambda: method.upper()

    return urllib2.urlopen(request).read()

def list2csv(items):
    q = deque(items)
    final = "%s" % q.popleft()
    while q:
        final += ",%s" % q.popleft()
    return final

def dedup_incidents(incidents_times):
    incidents_times.sort()
    after = []
    end_window = None
    for i in incidents_times:
        i_time = dateutil.parser.parse(i)
        if not end_window or i_time > end_window:
            after.append(i_time)
            end_window = i_time + INDIE_ALERT_WINDOW
    return after

if __name__ == '__main__':
    run()
