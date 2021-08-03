# -*- mode: ruby -*-
# vi: set ft=ruby :
Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/focal64"
  config.vm.synced_folder ".", "/vagrant"
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
  config.vm.provision "shell", inline: "mkdir -p /vagrant/deps", privileged: false

  # AUTOMATIC INSTALLATION: uncomment the packages that you want to be automatically
  # installed when running 'vagrant up' for the first time

  # Morty
  # config.vm.provision "shell", inline: "/vagrant/setup/install-rust.sh", privileged: false
  # config.vm.provision "shell", inline: "/vagrant/setup/install-morty.sh", privileged: false

  # Verilator
  # config.vm.provision "shell", inline: "/vagrant/setup/install-verilator.sh", privileged: false

  # KLayout
  # config.vm.provision "shell", inline: "/vagrant/setup/install-klayout.sh", privileged: false
  # config.vm.provision "shell", inline: "echo 'export QT_QPA_PLATFORM=offscreen' >> ~/.bashrc", privileged: false
  # OpenROAD
  # config.vm.provision "shell", inline: "/vagrant/setup/install-openroad.sh", privileged: false
  # config.vm.providion "shell", inline: "echo 'source /home/vagrant/siliconcompiler/deps/OpenROAD-flow-scripts/setup_env.sh' >> /home/vagrant/.bashrc", privileged: false

  # NextPNR and icestorm
  # config.vm.provision "shell", inline: "/vagrant/setup/install-ice40.sh", privileged: false

  # OpenFPGA
  # config.vm.provision "shell", inline: "/vagrant/setup/install-openfpga.sh", privileged: false

  # SureLog
  # config.vm.provision "shell", inline: "/vagrant/setup/install-surelog.sh", privileged: false

  # sv2v
  # config.vm.provision "shell", inline: "/vagrant/setup/install-sv2v.sh" privileged: false

  # siliconcompiler and python dependencies
  # config.vm.provision "shell", inline: "/vagrant/setup/install-py.sh", privileged: false
end
