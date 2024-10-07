import psutil
import platform
import time


class SystemMonitor:

    def get_cpu_usage(self):
        """Returns the current CPU usage as a percentage."""
        cpu_usage = psutil.cpu_percent(interval=1)
        return cpu_usage

    def get_memory_usage(self):
        """Returns the current memory usage."""
        memory_info = psutil.virtual_memory()
        memory_usage = {
            "total": memory_info.total,
            "available": memory_info.available,
            "used": memory_info.used,
            "percent": memory_info.percent
        }
        return memory_usage

    def get_disk_usage(self):
        """Returns the current disk usage."""
        disk_info = psutil.disk_usage('/')
        disk_usage = {
            "total": disk_info.total,
            "used": disk_info.used,
            "free": disk_info.free,
            "percent": disk_info.percent
        }
        return disk_usage

    def get_kernel_version(self):
        """Returns the kernel version of the system."""
        kernel_version = platform.uname().release
        return kernel_version

    def get_system_uptime(self):
        """Returns the system uptime."""
        boot_time = psutil.boot_time()
        current_time = time.time()
        uptime_seconds = current_time - boot_time
        uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime_seconds))
        return uptime_str

    def get_os_info(self):
        """Returns the name of the operating system."""
        os_info = platform.system()  # e.g., 'Linux', 'Windows', 'Darwin' for macOS
        return os_info

    def get_rpi_temperature_from_file(self):
        try:
            # Open the temperature file
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as file:
                # Read the temperature value
                temp_str = file.read().strip()
                # Convert to degrees Celsius
                temperature = int(temp_str) / 1000.0
                return temperature
        except Exception as e:
            print(f"Error: {e}")
            return None

    def display_system_info(self):
        """Prints the system information in a readable format."""
        print(f"Operating System: {self.get_os_info()}")

        print(f"Kernel Version: {self.get_kernel_version()}")
        print(f"System Uptime: {self.get_system_uptime()}")

        print(f"CPU Usage: {self.get_cpu_usage()}%")
        memory_usage = self.get_memory_usage()
        print(
            f"Memory Usage: {memory_usage['percent']}%")
        disk_usage = self.get_disk_usage()
        print(f"Disk Usage: {disk_usage['percent']}%")



