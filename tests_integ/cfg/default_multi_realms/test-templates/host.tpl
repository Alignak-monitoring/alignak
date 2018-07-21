define host{
    use                    test-host
    contact_groups         admins
    hostgroups             test
    host_name              host-%s
    address                127.0.0.1
}
