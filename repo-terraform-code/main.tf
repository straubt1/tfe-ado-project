resource "random_id" "server" {
  keepers = {
    # Always create
    timestamp = timestamp()
  }

  byte_length = 8
}

# resource "aws_s3_bucket" "main" {
#   bucket = "ado-test-bucket-delete-me-yes"
#   acl    = "private"

#   tags = {
#     Name  = "ado-test-bucket-delete-me-yes"
#     Owner = "tstraub"
#   }
# }
