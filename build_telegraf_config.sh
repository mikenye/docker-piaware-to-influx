

echo """[global_tags]

[agent]
  interval = "10s"
  round_interval = true
  metric_batch_size = 1000
  metric_buffer_limit = 10000
  collection_jitter = "0s"
  flush_interval = "10s"
  flush_jitter = "0s"
  precision = ""
  debug = false
  quiet = false
  logfile = ""
  hostname = ""
  omit_hostname = true

[[outputs.influxdb]]
  urls = ["http://192.168.69.35:8086"]
  database = "piaware"
  skip_database_creation = false
  timeout = "5s"

# Influx HTTP write listener
[[inputs.http_listener]]
  service_address = ":8186"
  read_timeout = "10s"
  write_timeout = "10s"
"""