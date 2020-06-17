resource "random_id" "server" {
  keepers = {
    # Always create
    timestamp = timestamp()
  }

  byte_length = 8
}