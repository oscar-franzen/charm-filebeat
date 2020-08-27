#!/usr/bin/python3
"""ElasticsearchCharm."""
import logging
import os
from pathlib import Path
import socket
import subprocess

from jinja2 import Environment, FileSystemLoader
from ops.charm import CharmBase
from ops.framework import (
    Object,
    StoredState,
)
from ops.main import main
from ops.model import (
    ActiveStatus,
    BlockedStatus,
)
from elasticsearch_requires import ElasticsearchRequires

logger = logging.getLogger()


class FilebeatCharm(CharmBase):
    """Operator charm for Filebeat."""
    stored = StoredState()

    def __init__(self, *args):
        """Initialize charm, configure states, and events to observe."""
        super().__init__(*args)
        self.elasticsearch = ElasticsearchRequires(self, "elasticsearch")
        self.stored.set_default(
            elasticsearch_ingresss=None,
        )
        event_handler_bindings = {
            self.on.install: self._on_install,
            self.on.start: self._on_start,
            self.elasticsearch.on.elasticsearch_available:
            self._on_elasticsearch_available,
        }
        for event, handler in event_handler_bindings.items():
            self.framework.observe(event, handler)

    def _on_install(self, event):
        """Install Filebeat"""
        subprocess.run(
            ["sudo", "dpkg", "-i", self.model.resources.fetch("filebeat")]
        )
        self.unit.status = ActiveStatus("Filebeat Installed")

    def _on_start(self, event):
        """Start Filebeat."""
        self.unit.status = BlockedStatus("Need relation to elasticsearch")

    def _on_elasticsearch_available(self, event):
        subprocess.run(["sudo", "-i", "service", "filebeat", "stop"])
        ctxt = {'elasticsearch_address': self.stored.elasticsearch_ingress}
        write_config(ctxt)
        subprocess.run(["sudo", "-i", "service", "filebeat", "start"])
        self.unit.status = ActiveStatus('Filebeat Started')


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
