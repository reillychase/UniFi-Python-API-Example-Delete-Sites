# UniFi-Python-API-Example-Delete-Sites
My https://hostifi.net auto UniFi provisioning script hit a bug and ended up creating 1,000+ sites for 1 user. I wrote this script real quick to go back and delete all sites containing that site description.

Could have retrieved the sites using the API, but instead I just grabbed them and dumped them manually from https://p01.hostifi.net:8443/api/self/sites and loaded them from a file.
