import sounddevice as sd

print("===Input Devices===")
print(sd.query_devices(kind="input"))
print("===Output Devices===")
print(sd.query_devices(kind="output"))