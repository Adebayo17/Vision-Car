sudo apt-get update && sudo apt-get upgrade
sudo apt-get install ninja-build pkg-config libyaml-dev python3-yaml python3-ply python3-jinja2 cmake mosquitto
sudo pip3 install meson wget
sudo pip3 install ultralytics

echo "Add to the end of the file ~/.bashrc : "
echo " export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/pi/.local/bin" "
nano ~/.bashrc
source ~/.bashrc

echo "Activate vnc server"
systemctl enabled vncserver-x11-serviced.service
systemctl status vncserver-x11-serviced.service

echo "The system will reboot..."
sudo reboot