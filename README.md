# nebman
Manage Nebula inventory and config generation.

## This is most definitely a WIP, needs much error checking and testing ##

Initial requirement is to simplify roll out of nebula to lab machines so:
- Add machines to a DB.
- Download Nebula files.
- Generate Nebula certificates.
- Generate Ansible files required to deploy.

Future requirements:

Initial version will be deploying to identical Linux machines so some content can be static, TODO:
- Find a better (non-static) way to generate the template files.
- Support for additional lighthouses (currently only 1 will be configured)
- Implement control over allowed services.
- Update Nebula feature.
- Support for Fedora as an endpoint.
- Support for Windows as an endpoint.


