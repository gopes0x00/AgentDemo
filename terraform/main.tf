provider "aws" {
  region = var.aws_region
  allowed_account_ids = var.aws_account_ids
}

resource "aws_instance" "ec2_instance" {
  count         = length(var.instance_names)
  ami           = "ami-0dfe0f1abee59c78d"
  key_name      = var.key_pair_name
  instance_type = "t2.nano"

  associate_public_ip_address = true

  security_groups = [aws_security_group.ssh_access.name]

    user_data = file(var.user_data_script)


  tags = {
    Name = var.instance_names[count.index]
  }
}

resource "aws_security_group" "ssh_access" {
  name        = "ssh-access"
  description = "Allow SSH inbound access"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

output "instance_public_ips" {
  description = "The public IPs of the created EC2 instances."
  value       = [aws_instance.ec2_instance[*].public_ip]
}