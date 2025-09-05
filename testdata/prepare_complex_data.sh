~/myh/instances/mariadb-10.6.22-linux-systemd-x86_64.10622/bin/mariadb -usstuser -psstpwd -h127.0.0.1 -P10622 ddlwizard_source_test  < /home/claudio/Projects/ddlwizard/testdata/complexdata/source_schema.sql
~/myh/instances/mariadb-10.6.22-linux-systemd-x86_64.10622/bin/mariadb -usstuser -psstpwd -h127.0.0.1 -P20622 ddlwizard_dest_test < /home/claudio/Projects/ddlwizard/testdata/complexdata/destination_schema.sql


