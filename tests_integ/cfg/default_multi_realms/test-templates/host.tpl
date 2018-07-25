define host{
    # File defined
    use                 test-host
    contact_groups      admins
    #hostgroups          ;allhosts
    host_name           host-%s-%s
    address             127.0.0.1
    realm               %s
}
