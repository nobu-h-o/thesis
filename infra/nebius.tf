terraform {
  required_providers {
    nebius = {
      source  = "terraform-provider.storage.eu-north1.nebius.cloud/nebius/nebius"
      version = ">= 0.5.55"
    }
  }
}

provider "nebius" {}

variable "user_data" {
  default = <<EOT
users:
 - name: notoh
   sudo: ALL=(ALL) NOPASSWD:ALL
   shell: /bin/bash
   ssh_authorized_keys:
    - ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFaQBp5NTbBYzLhqhCmD3gCBeWTMLCVTNY0gJwYy3USo
  EOT
}

resource "nebius_compute_v1_instance" "vm" {
  name = "peach-quelea-instance-9"
  parent_id = "project-e00y557apr00w8x0t57s9d"
  stopped = true
  resources = {
    platform = "gpu-l40s-a"
    preset = "1gpu-8vcpu-32gb"
  }
  boot_disk = {
    managed_disk = {
      name = "peach-quelea-instance-9-boot-disk"
      spec = {
        type = "NETWORK_SSD"
        block_size_bytes = 4096
        size_bytes = 268435456000
        source_image_family = {
          image_family = "ubuntu24.04-cuda13.0-serverless"
        }
      }
    }
    attach_mode = "READ_WRITE"
    device_id = "boot-disk"
  }
  network_interfaces = [
    {
      name = "eth0"
      subnet_id = "vpcsubnet-e00nmgw54h9gdy4vas"
      ip_address = {"allocationId":""}
      public_ip_address = {}
    }
  ]
  preemptible = {
    on_preemption = "STOP"
  }
  recovery_policy = "FAIL"
  cloud_init_user_data = var.user_data
  reservation_policy = {}
}