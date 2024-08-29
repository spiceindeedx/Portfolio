# Define AWS provider
provider "aws" {
  region = "eu-west-2"
}


# Create web VPC
resource "aws_vpc" "web_vpc_artem" {
  cidr_block = "10.1.0.0/16"
  tags = {
    Name = "web-vpc-artem"
  }
}

# Create shared VPC
resource "aws_vpc" "shared_vpc_artem" {
  cidr_block = "10.2.0.0/16"
  tags = {
    Name = "shared-vpc-artem"
  }
}

# Create web-pub subnet
resource "aws_subnet" "web_pub_subnet" {
  vpc_id            = aws_vpc.web_vpc_artem.id
  cidr_block        = "10.1.254.0/24"
  availability_zone = "eu-west-2a"
  tags = {
    Name = "web-pub"
  }
}

# Create shared subnet for nat-pub
resource "aws_subnet" "nat_pub_subnet" {
  vpc_id            = aws_vpc.shared_vpc_artem.id
  cidr_block        = "10.2.254.0/24"
  availability_zone = "eu-west-2a"
  tags = {
    Name = "nat-pub"
  }
}

# Create shared subnet for database
resource "aws_subnet" "database_subnet" {
  vpc_id            = aws_vpc.shared_vpc_artem.id
  cidr_block        = "10.2.2.0/24"
  availability_zone = "eu-west-2a"
  tags = {
    Name = "database"
  }
}

# Create internet gateway for web VPC
resource "aws_internet_gateway" "web_pub_igw" {
  vpc_id = aws_vpc.web_vpc_artem.id
  tags = {
    Name = "web-pub-igw"
  }
}

# Create internet gateway for shared VPC
resource "aws_internet_gateway" "shared_igw" {
  vpc_id = aws_vpc.shared_vpc_artem.id
  tags = {
    Name = "shared-igw"
  }
}

# Create route table for web-pub subnet
resource "aws_route_table" "web_pub_rt" {
  vpc_id = aws_vpc.web_vpc_artem.id
  tags = {
    Name = "web-pub-rt"
  }
}

# Create route table for nat-pub subnet
resource "aws_route_table" "nat_pub_rt" {
  vpc_id = aws_vpc.shared_vpc_artem.id
  tags = {
    Name = "nat-pub-rt"
  }
}

# Create route table for database subnet
resource "aws_route_table" "database_rt" {
  vpc_id = aws_vpc.shared_vpc_artem.id
  tags = {
    Name = "database-rt"
  }
}

# Create route table for shared VPC
resource "aws_route_table" "shared_rt" {
  vpc_id = aws_vpc.shared_vpc_artem.id
  tags = {
    Name = "shared-rt"
  }
}


# Update route in web-pub-rt to point to web-pub-igw for internet access
resource "aws_route" "web_pub_to_internet" {
  route_table_id            = aws_route_table.web_pub_rt.id
  destination_cidr_block    = "0.0.0.0/0"
  gateway_id                = aws_internet_gateway.web_pub_igw.id
}

# # Update route in web-pub-rt for peering connection
# resource "aws_route" "web_pub_to_shared_peering" {
#   route_table_id            = aws_route_table.web_pub_rt.id
#   destination_cidr_block    = "10.2.2.0/24"
#   vpc_peering_connection_id = aws_vpc_peering_connection.peer.id
# }

# Add new route in nat-pub-rt to point to shared-igw for internet access
resource "aws_route" "nat_pub_to_internet" {
  route_table_id            = aws_route_table.nat_pub_rt.id
  destination_cidr_block    = "0.0.0.0/0"
  gateway_id                = aws_internet_gateway.shared_igw.id
}

# Add new route in database-rt for peering connection
resource "aws_route" "database_to_web_peering" {
  route_table_id            = aws_route_table.database_rt.id
  destination_cidr_block    = "10.1.254.0/24"
  vpc_peering_connection_id = aws_vpc_peering_connection.peer.id
}

# # Update route in shared-rt for peering connection
# resource "aws_route" "shared_to_web_peering" {
#   route_table_id            = aws_route_table.shared_rt.id
#   destination_cidr_block    = "10.1.254.0/24"
#   vpc_peering_connection_id = aws_vpc_peering_connection.peer.id
# }

# Get the network interface ID of the nat_pub_artem instance
data "aws_instance" "nat_pub_instance" {
  instance_id = aws_instance.nat_pub_artem.id
}

data "aws_network_interfaces" "nat_pub_eni" {
  filter {
    name   = "attachment.instance-id"
    values = [data.aws_instance.nat_pub_instance.id]
  }
}

# Add new route in shared-rt to point to network interface of nat1 instance for internet access
resource "aws_route" "shared_to_nat_instance" {
  route_table_id            = aws_route_table.shared_rt.id
  destination_cidr_block    = "0.0.0.0/0"
  network_interface_id      = data.aws_network_interfaces.nat_pub_eni.ids[0]
}



# Associate web-pub subnet with web-pub route table
resource "aws_route_table_association" "web_pub_assoc" {
  subnet_id      = aws_subnet.web_pub_subnet.id
  route_table_id = aws_route_table.web_pub_rt.id
}

# Associate nat-pub subnet with nat-pub route table
resource "aws_route_table_association" "nat_pub_assoc" {
  subnet_id      = aws_subnet.nat_pub_subnet.id
  route_table_id = aws_route_table.nat_pub_rt.id
}

# Associate database subnet with shared route table
resource "aws_route_table_association" "database_assoc_shared_rt" {
  subnet_id      = aws_subnet.database_subnet.id
  route_table_id = aws_route_table.shared_rt.id
}


# Create web-pub security group
resource "aws_security_group" "web_pub_sg" {
  vpc_id = aws_vpc.web_vpc_artem.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    cidr_blocks = ["10.2.2.0/24"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "web-pub-sg"
  }
}

# Create nat-pub security group
resource "aws_security_group" "nat_pub_sg" {
  vpc_id = aws_vpc.shared_vpc_artem.id

  ingress {
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    cidr_blocks = ["10.2.0.0/16"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["10.2.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "nat-pub-sg"
  }
}

# Create database security group
resource "aws_security_group" "database_sg" {
  vpc_id = aws_vpc.shared_vpc_artem.id

  ingress {
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    cidr_blocks = ["10.2.0.0/16"]
  }

  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["10.1.254.0/24"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.2.0.0/16"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["192.168.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "database-sg"
  }
}


data "aws_eip" "web_pub_eip" {
  id = "eipalloc-0a220d24622066246"
}

# Create web-pub EC2 instance
resource "aws_instance" "web_pub_artem" {
  ami             = "ami-0d0bcde4344ece910"
  instance_type   = "t2.micro"
  subnet_id       = aws_subnet.web_pub_subnet.id
  private_ip      = "10.1.254.10"
  key_name        = aws_key_pair.my_keypair_web.key_name
  security_groups = [aws_security_group.web_pub_sg.id]

  tags = {
    Name = "web-pub-artem"
  }
}

resource "aws_key_pair" "my_keypair_web" {
  key_name   = "web_key"
  public_key = file("${path.module}/web_key.pub")
}


data "aws_eip" "nat_pub_eip" {
  id = "eipalloc-0b5790126537792b7"
}

# Create nat-pub EC2 instance
resource "aws_instance" "nat_pub_artem" {
  ami           = "ami-007fbd798d63d6711"
  instance_type = "t2.micro"
  subnet_id     = aws_subnet.nat_pub_subnet.id
  private_ip    = "10.2.254.254"
  key_name        = aws_key_pair.my_keypair_nat_db.key_name
  security_groups = [aws_security_group.nat_pub_sg.id]
  source_dest_check = false

  tags = {
    Name = "nat-pub-artem"
  }
}

# Create db1 EC2 instance
resource "aws_instance" "db1_artem" {
  ami           = "ami-0d0bcde4344ece910"
  instance_type = "t2.micro"
  subnet_id     = aws_subnet.database_subnet.id
  private_ip    = "10.2.2.41"
  key_name        = aws_key_pair.my_keypair_nat_db.key_name
  security_groups = [aws_security_group.database_sg.id]

  tags = {
    Name = "db1"
  }
}

resource "aws_key_pair" "my_keypair_nat_db" {
  key_name   = "nat_db"
  public_key = file("${path.module}/nat_db.pub")
}


# # Create Elastic IP for web-pub instance
# resource "aws_eip" "web_pub_eip" {
#   instance = aws_instance.web_pub_artem.id
# }

# Associate Elastic IP with web-pub instance
resource "aws_eip_association" "web_pub_eip_assoc" {
  instance_id   = aws_instance.web_pub_artem.id
  allocation_id = "eipalloc-0a220d24622066246"
}

# # Create Elastic IP for nat-pub instance
# resource "aws_eip" "nat_pub_eip" {
#   instance = aws_instance.nat_pub_artem.id
# }

# Associate Elastic IP with nat-pub instance
resource "aws_eip_association" "nat_pub_eip_assoc" {
  instance_id   = aws_instance.nat_pub_artem.id
  allocation_id = "eipalloc-0b5790126537792b7"
}

# Create peering connection
resource "aws_vpc_peering_connection" "peer" {
  peer_vpc_id          = aws_vpc.shared_vpc_artem.id
  vpc_id               = aws_vpc.web_vpc_artem.id 
  auto_accept          = true
  tags = {
    Name = "web-shared-pcx"
  }
}

# Create route from web-pub route table to shared route table
resource "aws_route" "web_pub_to_shared" {
  route_table_id            = aws_route_table.web_pub_rt.id
  destination_cidr_block    = "10.2.2.0/24"
  vpc_peering_connection_id = aws_vpc_peering_connection.peer.id
}

# Create route from shared route table to web-pub route table
resource "aws_route" "shared_to_web_pub" {
  route_table_id            = aws_route_table.shared_rt.id
  destination_cidr_block    = "10.1.254.0/24"
  vpc_peering_connection_id = aws_vpc_peering_connection.peer.id
}



