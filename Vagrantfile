# -*- mode: ruby -*-
# vi: set ft=ruby :
Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/focal64"
  config.vm.synced_folder ".", "/vagrant", disabled: true
  config.vm.synced_folder ".", "/home/vagrant/siliconcompiler/"

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "8192"
    vb.cpus = 4
    vb.customize ["modifyvm", :id, "--uart1", "0x3F8", "4"]
    vb.customize ["modifyvm", :id, "--uartmode1", "file", File::NULL]
  end

  config.vm.provision "shell", inline: <<-SHELL
    systemctl disable apt-daily.service
    systemctl disable apt-daily.timer
  SHELL
  config.vm.provision "shell", inline: "sudo apt-get update", privileged: false
  config.vm.provision "shell", inline: "mkdir /vagrant/deps", privileged: false
  config.vm.provision "shell", inline: "/vagrant/setup/install-verilator.sh", privileged: false
  config.vm.provision "shell", inline: "/vagrant/setup/install-klayout.sh", privileged: false
  config.vm.provision "shell", inline: "echo 'export QT_QPA_PLATFORM=offscreen' >> ~/.bashrc", privileged: false
  config.vm.provision "shell", inline: "/vagrant/setup/install-openroad.sh", privileged: false
  config.vm.providion "shell", inline: "echo 'source /home/vagrant/siliconcompiler/deps/OpenROAD-flow-scripts/setup_env.sh' >> /home/vagrant/.bashrc", privileged: false
  config.vm.provision "shell", inline: "/vagrant/setup/install-ice40.sh", privileged: false
  config.vm.provision "shell", inline: "/vagrant/setup/install-openfpga.sh", privileged: false
  config.vm.provision "shell", inline: "/vagrant/setup/install-py.sh", privileged: false
end
