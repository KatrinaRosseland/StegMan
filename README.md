# StegMan
Python covert channel that transfers data through hangman letter guesses to another client through HTTPS POST requests uploading images with the first pixel red value encoded with the ACSII value of the letter input. Full GUI for client side and packaged executable for both server and client side. Uses self signed cert.

How to run:
- WAN/Remote (must set port forwarding on router for port 5000/ whatever port you use)
    - Listener: Run as listening service -> Remote listen -> initialize. Run ipconfig to identify public IP
    - Sender: run as client game -> remote server deployment -> target deployment address (iaddress from ipconfig of remote           host)
- LAN
  - Remote Device:
      - Listener: Run as listening service -> Remote listen -> initialize. Run ipconfig to identify public IP
      - Sender: run as client game -> remote server deployment -> target deployment address (iaddress from ipconfig of remote           host)
  - Your device -> your device
      - Listener: localhost mode -> initalize
      - Sender: Localhost sandbox -> initialize
