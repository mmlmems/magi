#! /bin/bash

# Prepare Pi for MAGI server code
#
# Script must be executable: chmod +x setup.sh
# Run with sudo

echo "==========================================="
echo "Synchronizing system time"
echo "==========================================="
sudo timedatectl

echo "==========================================="
echo "Setting up 25 MB RAM disk"
echo "==========================================="
FSTAB_LINE="tmpfs /path/to/ramdisk tmpfs defaults,size=25M 0 0"
if grep -Fxq "$FSTAB_LINE" /etc/fstab; then
    echo "RAM disk already set up in /etc/fstab"
else
    echo "Backing up /etc/fstab to /etc/fstab.bak"
    sudo cp /etc/fstab /etc/fstab.bak
    echo "Adding the line to /etc/fstab"
    echo "$FSTAB_LINE" | sudo tee -a /etc/fstab > /dev/null
    echo "Line added successfully. Verify /etc/fstab before rebooting."
fi

echo "==========================================="
echo "Adding crontab entry to run MAGI server at boot"
echo "==========================================="
# Delete any existing crontab entries:
crontab -r
CRON_SCHEDULE="@reboot"
CURRENT_USER=$(logname)
COMMAND="cd /home/$CURRENT_USER/magi && python3 -u /home/$CURRENT_USER/magi/magi_server.py >> /home/$CURRENT_USER/magi/magi_server.log 2>&1"
CRON_ENTRY="$CRON_SCHEDULE $COMMAND"
# Check if the cron job already exists:
(sudo -u "$CURRENT_USER" crontab -l 2>/dev/null | grep -Fxq "$CRON_ENTRY") || {
    # Append the new cron job to the existing crontab:
    (sudo -u "$CURRENT_USER" crontab -l 2>/dev/null; echo "$CRON_ENTRY") | sudo -u "$CURRENT_USER" crontab -
    echo "Crontab entry added successfully."
}
echo "Current crontab:"
sudo -u "$CURRENT_USER" crontab -l

echo "==========================================="
echo "apt-get update"
echo "==========================================="
sudo apt-get update

echo "==========================================="
echo "apt-get upgrade (may take 30+ min)"
echo "(use apt-get full-upgrade if old packages"
echo "need to be removed)"
echo "==========================================="
sudo apt-get upgrade

echo "==========================================="
echo "pip"
echo "==========================================="
sudo apt install python3-pip

echo "==========================================="
echo "picamera2"
echo "==========================================="
sudo apt-get --yes install python3-picamera2

echo "==========================================="
echo "libcamera (SHOULD BE PREINSTALLED -- UNCOMMENT IF NEEDED)"
echo "==========================================="
# sudo apt-get --yes install python3-libcamera

echo "==========================================="
echo "matplotlib"
echo "==========================================="
sudo apt-get --yes install python3-matplotlib

echo "==========================================="
echo "numpy"
echo "==========================================="
sudo apt-get --yes install python3-numpy

echo "==========================================="
echo "scipy"
echo "==========================================="
sudo apt-get --yes install python3-scipy

echo "==========================================="
echo "pandas"
echo "(may break on sympy setup, continue"
echo " installation manually if necessary)"
echo "==========================================="
sudo apt-get --yes install python3-pandas

echo "==========================================="
echo "simple-pid"
echo "==========================================="
sudo python3 -m pip install --break-system-packages simple-pid

echo "==========================================="
echo "              SETUP COMPLETE"
echo "==========================================="