# Generated visual assurance manifest

Source: `49798c84e14a298cead9473f90814c06297f0409`  
Baselines: 56  
Inventory SHA-256: `766a311dba3656d140a5e8fe76ffbd331fab0ecc5ffe14bffe2642f8ff9fa220`

| Route class | Target | Authentication | Proof boundary |
|---|---|---|---|
| public | `woodkilldev.com/` | public | hermetic |
| admin | `admin.woodkilldev.com/admin` | edge+django+csrf | live approval required |
| api | `woodkilldev.com/api` | edge+api | live approval required |
| swagger | `swagger.woodkilldev.com/docs` | edge | live approval required |
| pgadmin | `pgadmin.woodkilldev.com/` | edge+pgadmin | live approval required |
| traefik | `traefik.woodkilldev.com/` | edge | live approval required |

Protected-route rows are contracts, not claims of live availability. Live proof requires a separately approved ephemeral preview.
