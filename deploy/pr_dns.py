import os

import boto
from boto.route53.record import ResourceRecordSets

zone_id = os.environ['PR_ZONE']
pr_number = os.environ['CIRCLE_BRANCH'].split("/", 1)[1]
cname = "%s.pr.digital.rackspace.com" % pr_number

conn = boto.connect_route53()
changes = ResourceRecordSets(conn, zone_id)
change = changes.add_change("CREATE", pr_number, "CNAME")
change.add_value("lb.lb.prs.rancher.digital.rackspace.com")
# changes.commit()
