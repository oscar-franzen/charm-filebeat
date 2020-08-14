#!/usr/bin/python3
"""ElasticsearchCharm."""
import logging
import os
from pathlib import Path
import socket
import subprocess

from jinja2 import Environment, FileSystemLoader
from ops.charm import CharmBase
from ops.framework import Object
from ops.main import main
from ops.model import ActiveStatus


logger = logging.getLogger()


class ElasticsearchProvides(Object):
    """Provide host."""

    def __init__(self, charm, relation_name):
        """Set data on relation created."""
        super().__init__(charm, relation_name)

        self.framework.observe(
            charm.on[relation_name].relation_created,
            self.on_relation_created
        )

    def on_relation_created(self, event):
        """Set host on relation created."""
        event.relation.data[self.model.unit]['host'] = socket.gethostname().split(".")[0]


class FilebeatCharm(CharmBase):
    """Operator charm for Elasticsearch."""

    def __init__(self, *args):
        """Initialize charm, configure states, and events to observe."""
        super().__init__(*args)
        self.elastic_search = ElasticsearchProvides(self, "elasticsearch")
        event_handler_bindings = {
            self.on.install: self._on_install,
        }
        for event, handler in event_handler_bindings.items():
            self.framework.observe(event, handler)

    def _on_install(self, event):
        """Install ElasticSearch."""
        subprocess.run(
            ["sudo", "dpkg", "-i", self.model.resources.fetch("filebeat")]
        )
        open_port(9200)
        host_name = socket.gethostname()
        ctxt = {"hostname": host_name}
        #write_config(ctxt)
        self.unit.status = ActiveStatus("Elasticsearch Installed")



def write_config(context):
    """Render the context to a template.

    target: /etc/elasticsearch/elasticsearch.yml
    source: /templates/elasticsearch.yml.tmpl
    file name can also be slurmdbdb.conf
    """
    template_name = "filebeat.yml.tmpl"
    template_dir = "templates"
    target = Path("/etc/filebeat/filebeat.yml")
    logger.info(os.getcwd())
    rendered_template = Environment(
        loader=FileSystemLoader(template_dir)
    ).get_template(template_name)

    target.write_text(rendered_template.render(context))


def _modify_port(start=None, end=None, protocol='tcp', hook_tool="open-port"):
    assert protocol in {'tcp', 'udp', 'icmp'}
    if protocol == 'icmp':
        start = None
        end = None

    if start and end:
        port = f"{start}-{end}/"
    elif start:
        port = f"{start}/"
    else:
        port = ""
    subprocess.run([hook_tool, f"{port}{protocol}"])


def open_port(start, end=None, protocol="tcp"):
    """Open port in operator charm."""
    _modify_port(start, end, protocol=protocol, hook_tool="open-port")


if __name__ == "__main__":
    main(FilebeatCharm)
