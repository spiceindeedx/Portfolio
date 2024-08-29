output "db1_private_ip" {
  value = aws_instance.db1_artem.private_ip
}

output "web_pub_eip" {
  value = data.aws_eip.web_pub_eip.public_ip
}

output "nat_pub_eip" {
  value = data.aws_eip.nat_pub_eip.public_ip
}
