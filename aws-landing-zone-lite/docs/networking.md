# Networking notes

## What the `network` module builds today

One VPC, two public and two private subnets across two availability zones, an internet gateway,
separate route tables, a locked-down default security group, and VPC flow logs to CloudWatch.
Private subnets have **no** internet route. A NAT gateway is billed hourly, so it is left out;
add one (or VPC endpoints for AWS services) when a workload needs outbound access.

```mermaid
flowchart TB
    igw[Internet gateway] --> pub
    subgraph vpc[VPC 10.0.0.0/16]
        subgraph pub[Public subnets x2]
            lb[Load balancers, bastions]
        end
        subgraph priv[Private subnets x2]
            app[Application workloads]
        end
        pub --> priv
    end
    vpc -.-> flow[Flow logs in CloudWatch]
```

## Hub-and-spoke: how this would grow (design pattern, not built here)

In a real landing zone each workload account gets its own VPC (a spoke). A shared network account
holds a hub with a transit gateway, central egress (NAT, firewall) and a link to on-premises
networks (VPN or Direct Connect). Spokes talk to each other and out through the hub only, so
traffic inspection and routing rules live in one place.

```mermaid
flowchart LR
    onprem[On-premises network] <-->|VPN / Direct Connect| tgw[Transit gateway in hub]
    tgw <--> prod[Spoke: prod VPC]
    tgw <--> dev[Spoke: dev VPC]
    tgw <--> shared[Spoke: shared services VPC]
    tgw --> egress[Central egress: NAT / firewall] --> internet[Internet]
```

This repo's `network` module is the building block for a spoke. Transit gateway attachments and
the hub account are a possible next step; they are not implemented.
