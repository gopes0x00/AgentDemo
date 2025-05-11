variable "key_pair_name" {
  description = "The name of the SSH key pair to use for the instances."
  type        = string
}

variable "instance_names" {
  description = "A list of names for the EC2 instances."
  type        = list(string)
  default     = ["Prod_Server", "Attacker"]
}

variable "aws_region" {
    description = "required AWS region"
    type = string
    default = "eu-west-1"

}

variable "aws_account_ids" {
    description = "allowed AWS account IDs"
    type = list(string)
    default = [""]
}

variable "user_data_script" {
  description = "The path to the user data script to run on instance launch."
  type        = string
  default     = ""
}