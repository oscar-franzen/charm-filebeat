#!/usr/bin/python3
"""FilebeatCharm."""
from elastic_ops_manager import ElasticOpsManager
from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus


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

    def _on_handle_config(self, event):
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
