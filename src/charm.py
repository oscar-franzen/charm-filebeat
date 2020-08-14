#!/usr/bin/python3
"""FilebeatCharm."""
import logging
import pathlib
import subprocess

from jinja2 import (
    Environment,
    FileSystemLoader,
)
from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus


logger = logging.getLogger()


OS_RELEASE = pathlib.Path("/etc/os-release").read_text().split("\n")
OS_RELEASE_CTXT = {
    k: v.strip("\"")
    for k, v in [item.split("=") for item in OS_RELEASE if item != '']
}

TEMPLATE_DIR = pathlib.Path("./src/templates")


def _render_template(template_name, target, context):
    rendered_template = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR))
    ).get_template(template_name)
    target.write_text(rendered_template.render(context))


class ElasticOpsManager:

    def __init__(self, elastic_service):
        self._os = OS_RELEASE_CTXT['ID']
        self._version_id = OS_RELEASE_CTXT['VERSION_ID']
        self._elastic_service = elastic_service
        self._config_file_path = pathlib.Path(
            f"/etc/{elastic_service}/{elastic_service}.yml"
        )
        self._config_template_name = f"{elastic_service}.yml.j2"

    def install(self, resource):
        self._install_java()
        self._install_elastic_resource(resource)

    def _install_elastic_resource(self, resource):
        if self._os == 'ubuntu':
            subprocess.call([
                "dpkg",
                "-i",
                resource
            ])
        elif self._os == 'centos':
            subprocess.call([
                "rpm",
                "--install",
                resource
            ])

    def _install_java(self):
        if self._os == 'ubuntu':
            subprocess.call(["apt", "update", "-y"])
            if self._version_id in ['20.04', '18.04']:
                subprocess.call(["apt", "install", "openjdk-8-jre-headless", "-y"])
        elif self._os == 'centos':
            if self._version_id == '7':
                subprocess.call(["yum", "update", "-y"])
                subprocess.call(["yum", "install", "java-1.8.0-openjdk-headless", "-y"])
            elif self._version_id == '8':
                subprocess.call(["dnf", "update", "-y"])
                subprocess.call(["dnf", "install", "java-1.8.0-openjdk-headless", "-y"])

    def start_elastic_service(self):
        subprocess.call([
            "systemctl",
            "enable",
            self._elastic_service
        ])
        subprocess.call([
            "systemctl",
            "start",
            self._elastic_service
        ])

    def render_config_and_restart(self, context):
        # Remove the pre-existing config
        if self._config_file_path.exists():
            self._config_file_path.unlink()

        # Write /etc/filebeat/filebeat.yml
        _render_template(
            self._config_template_name,
            self._config_file_path,
            context
        )

        # Restart filebeat service
        subprocess.call([
            "systemctl",
            "restart",
            self._elastic_service
        ])


class FilebeatCharm(CharmBase):
    """Filebeat charm."""

    def __init__(self, *args):
        """Initialize charm, configure states, and events to observe."""
        super().__init__(*args)

        self._elastic_ops_manager = ElasticOpsManager("filebeat")

        event_handler_bindings = {
            self.on.install: self._on_install,
            self.on.start: self._on_start,
            self.on.upgrade_charm: self._on_upgrade_charm,
            self.on.config_changed: self._on_handle_config,
        }
        for event, handler in event_handler_bindings.items():
            self.framework.observe(event, handler)

    def _on_install(self, event):
        resource = self.model.resources.fetch('elastic-resource')
        self._elastic_ops_manager.install(resource)
        self.unit.status = ActiveStatus("Filebeat installed")

    def _on_start(self, event):
        self._elastic_ops_manager.start_elastic_service()
        self.unit.status = ActiveStatus("Filebeat available")

    def _on_upgrade_charm(self, event):
        pass

    def _handle_config(self, event):
        ctxt = {
            'elasticsearch_hosts': [],
            'logpath': self.model.config.get('logpath').split(" ")
        }

        user_provided_elasticsearch_hosts = \
            self.model.config.get('elasticsearch-hosts')

        if user_provided_elasticsearch_hosts:
            ctxt['elasticsearch_hosts'] = \
                user_provided_elasticsearch_hosts.split(",")

        self._elastic_ops_manager.render_config_and_restart(ctxt)


if __name__ == "__main__":
    main(FilebeatCharm)
