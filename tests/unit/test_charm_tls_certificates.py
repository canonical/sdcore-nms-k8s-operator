# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import os
import tempfile

import scenario
from ops import testing

from tests.unit.certificates_helpers import example_cert_and_key
from tests.unit.fixtures import NMSTlsCertificatesFixtures


class TestCharmTlsCertificates(NMSTlsCertificatesFixtures):
    def test_given_certificates_are_stored_when_on_certificates_relation_broken_then_certificates_are_removed(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            certificates_relation = testing.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            certs_mount = testing.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            config_mount = testing.Mount(
                location="/nms/config",
                source=tempdir,
            )
            container = testing.Container(
                name="nms",
                can_connect=True,
                mounts={"certs": certs_mount, "config": config_mount},
            )
            os.mkdir(f"{tempdir}/support")
            os.mkdir(f"{tempdir}/support/TLS")
            with open(f"{tempdir}/nms.pem", "w") as f:
                f.write("certificate")

            with open(f"{tempdir}/nms.key", "w") as f:
                f.write("private key")

            with open(f"{tempdir}/ca.pem", "w") as f:
                f.write("CA certificate")

            state_in = testing.State(
                relations=[certificates_relation],
                containers=[container],
                leader=True,
            )

            self.ctx.run(self.ctx.on.relation_broken(certificates_relation), state_in)

            assert not os.path.exists(f"{tempdir}/nms.pem")
            assert not os.path.exists(f"{tempdir}/nms.key")
            assert not os.path.exists(f"{tempdir}/ca.pem")

    def test_given_cannot_connect_to_container_when_on_certificates_relation_broken_then_certificates_are_not_removed(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            certificates_relation = testing.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            certs_mount = testing.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            config_mount = testing.Mount(
                location="/nms/config",
                source=tempdir,
            )
            container = testing.Container(
                name="nms",
                can_connect=False,
                mounts={"certs": certs_mount, "config": config_mount},
            )
            os.mkdir(f"{tempdir}/support")
            os.mkdir(f"{tempdir}/support/TLS")
            with open(f"{tempdir}/nms.pem", "w") as f:
                f.write("certificate")

            with open(f"{tempdir}/nms.key", "w") as f:
                f.write("private key")

            with open(f"{tempdir}/ca.pem", "w") as f:
                f.write("CA certificate")

            state_in = testing.State(
                relations=[certificates_relation],
                containers=[container],
                leader=True,
            )

            self.ctx.run(self.ctx.on.relation_broken(certificates_relation), state_in)

            assert os.path.exists(f"{tempdir}/nms.pem")
            assert os.path.exists(f"{tempdir}/nms.key")
            assert os.path.exists(f"{tempdir}/ca.pem")

    def test_given_certificate_matches_stored_one_when_pebble_ready_then_certificate_is_not_pushed(
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "apple",
                    "password": "hamburger",
                    "uris": "1.2.3.4:1234",
                },
            )
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={"config": config_mount, "certs": certs_mount},
            )
            state_in = testing.State(
                leader=True,
                relations=[
           auth_database_relation,
                    common_database_relation,
                    certificates_relation,
                ],
                containers={container},
            )
            provider_certificate, private_key = example_cert_and_key(
                relation_id=certificates_relation.id
            )
            self.mock_get_assigned_certificate.return_value = (provider_certificate, private_key)
            with open(f"{tempdir}/nms.pem", "w") as f:
                f.write(str(provider_certificate.certificate))
            with open(f"{tempdir}/nms.key", "w") as f:
                f.write(str(private_key))
            with open(f"{tempdir}/ca.pem", "w") as f:
                f.write(str(provider_certificate.ca))
            config_modification_time_nms_pem = os.stat(tempdir + "/nms.pem").st_mtime
            config_modification_time_nms_key = os.stat(tempdir + "/nms.key").st_mtime
            config_modification_time_ca_pem = os.stat(tempdir + "/ca.pem").st_mtime

            self.ctx.run(self.ctx.on.pebble_ready(container=container), state_in)

            assert os.stat(tempdir + "/nms.pem").st_mtime == config_modification_time_nms_pem
            assert os.stat(tempdir + "/nms.key").st_mtime == config_modification_time_nms_key
            assert os.stat(tempdir + "/ca.pem").st_mtime == config_modification_time_ca_pem

    def test_given_storage_attached_and_certificate_available_when_pebble_ready_then_certs_are_written(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.9.11.4:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.8.11.4:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    certificates_relation,
                },
            )
            provider_certificate, private_key = example_cert_and_key(
                relation_id=certificates_relation.id
            )
            self.mock_get_assigned_certificate.return_value = (provider_certificate, private_key)

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            with open(tempdir + "/nms.pem", "r") as f:
                assert f.read() == str(provider_certificate.certificate)
            with open(tempdir + "/nms.key", "r") as f:
                assert f.read() == str(private_key)
            with open(tempdir + "/ca.pem", "r") as f:
                assert f.read() == str(provider_certificate.ca)

    def test_given_certificate_exist_and_are_different_when_pebble_ready_then_certs_are_overwritten(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.9.11.4:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.8.11.4:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            os.mkdir(f"{tempdir}/support")
            os.mkdir(f"{tempdir}/support/TLS")
            old_provider_certificate, old_private_key = example_cert_and_key(
                relation_id=auth_database_relation.id
            )
            with open(f"{tempdir}/nms.pem", "w") as f:
                f.write(str(old_provider_certificate.certificate))

            with open(f"{tempdir}/nms.key", "w") as f:
                f.write(str(old_private_key))

            with open(f"{tempdir}/ca.pem", "w") as f:
                f.write(str(old_provider_certificate.ca))

            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    certificates_relation,
                },
            )
            new_provider_certificate, new_private_key = example_cert_and_key(
                relation_id=certificates_relation.id
            )
            assert new_provider_certificate.certificate != old_provider_certificate.certificate
            assert new_provider_certificate.ca != old_provider_certificate.ca
            assert new_private_key != old_private_key

            self.mock_get_assigned_certificate.return_value = (
                new_provider_certificate,
                new_private_key
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            with open(tempdir + "/nms.pem", "r") as f:
                assert f.read() == str(new_provider_certificate.certificate)
            with open(tempdir + "/nms.key", "r") as f:
                assert f.read() == str(new_private_key)
            with open(tempdir + "/ca.pem", "r") as f:
                assert f.read() == str(new_provider_certificate.ca)


