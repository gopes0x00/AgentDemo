#! /bin/bash
sudo sysctl -w vm.max_map_count=262144

# create the network so elastic and kibana can talk
podman network create elastic

echo running kibana and elastic containers
podman run -d --name kib01 --net elastic -p 5601:5601 docker.elastic.co/kibana/kibana-wolfi:sha256-ffdbff6b7b937b64aad0f1f827194e3c9abdde514f9595aa8e2e9346d6b5c7ee
podman run --name es01 --net elastic -p 9200:9200 -d -m 2GB docker.elastic.co/elasticsearch/elasticsearch:sha256-fffb0fb3d8305caded6bdfc7c2308133d3a67e71a4011e9867b9a2c3a7a3a7e5
echo sleeping for 60 seconds to allow setup 
sleep 60

echo Set elastic password
podman exec -it es01 /usr/share/elasticsearch/bin/elasticsearch-reset-password -u elastic

echo Get kibana URL
podman logs kib01 | grep 5601

echo Create kibana enrollment token
podman exec -it es01 /usr/share/elasticsearch/bin/elasticsearch-create-enrollment-token -s kibana

#https://medium.com/@anandgvyas/spin-up-your-elastic-stack-playground-using-podman-43d23f8d74bb
