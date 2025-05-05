import dns.resolver
import time
import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import subprocess
import sys
import ctypes


DNS_PROVIDERS = {
    "Cloudflare": ["1.1.1.1", "1.0.0.1"],
    "Google": ["8.8.8.8", "8.8.4.4"],
    "OpenDNS": ["208.67.222.222", "208.67.220.220"],
    "Quad9": ["9.9.9.9", "149.112.112.112"],
    "AdGuard": ["94.140.14.14", "94.140.15.15"],
    "Ручной ввод": ["", ""]
}

class DNSBenchmark:
    def __init__(self):
        self.timeout = 5  

    def test_dns_server(self, dns_server, domain="example.com"):
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [dns_server]
        resolver.timeout = self.timeout
        resolver.lifetime = self.timeout

        start_time = time.time()
        try:
            resolver.resolve(domain, 'A') 
            response_time = (time.time() - start_time) * 1000  
            return response_time
        except (dns.resolver.NoNameservers, dns.resolver.Timeout, dns.resolver.NoAnswer):
            return None
        except Exception as e:
            print(f"Ошибка при проверке {dns_server}: {str(e)}")
            return None

    def start_test(self, dns_servers):
        results = {}
        for server in dns_servers:
            response_time = self.test_dns_server(server)
            if response_time is not None:
                results[server] = response_time
        return results

class DNSChangerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DNS Master Pro")
        self.root.resizable(False, False)
        self.benchmark = None
        self.setup_ui()
        self.check_admin()
        self.update_interfaces()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.grid(row=0, column=0)

        ttk.Label(main_frame, text="Сетевой интерфейс:").grid(row=0, column=0, sticky="w")
        self.interface_combo = ttk.Combobox(main_frame, state="readonly", width=30)
        self.interface_combo.grid(row=0, column=1, pady=5)

        ttk.Label(main_frame, text="DNS провайдер:").grid(row=1, column=0, sticky="w")
        self.dns_combo = ttk.Combobox(main_frame, values=list(DNS_PROVIDERS.keys()), state="readonly", width=30)
        self.dns_combo.grid(row=1, column=1, pady=5)
        self.dns_combo.current(0)
        self.dns_combo.bind("<<ComboboxSelected>>", self.update_dns_field)

        self.manual_frame = ttk.Frame(main_frame)
        ttk.Label(self.manual_frame, text="Основной DNS:").grid(row=0, column=0)
        self.primary_entry = ttk.Entry(self.manual_frame, width=15)
        self.primary_entry.grid(row=0, column=1, padx=5)
        ttk.Label(self.manual_frame, text="Альтернативный DNS:").grid(row=1, column=0)
        self.secondary_entry = ttk.Entry(self.manual_frame, width=15)
        self.secondary_entry.grid(row=1, column=1, padx=5)

        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.status_label = ttk.Label(main_frame, text="")

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=15)
        
        ttk.Button(btn_frame, text="Найти лучший DNS", command=self.start_benchmark).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Применить", command=self.apply_dns).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Сбросить", command=self.reset_dns).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Выход", command=self.root.destroy).pack(side=tk.RIGHT, padx=5)

    def start_benchmark(self):
        self.progress.grid(row=4, column=0, columnspan=2, pady=5, sticky="ew")
        self.progress.start()
        self.status_label.config(text="Тестирование DNS-серверов...")
        self.status_label.grid(row=3, column=0, columnspan=2)
        
        dns_servers = []
        for provider in DNS_PROVIDERS.values():
            dns_servers.extend(provider)
        dns_servers = list(set([s for s in dns_servers if s]))  

        self.benchmark = DNSBenchmark()
        results = self.benchmark.start_test(dns_servers)
        
        self.progress.stop()
        self.progress.grid_forget()
        self.status_label.grid_forget()
        
        if results:
            best_server = min(results, key=results.get)
            best_time = results[best_server]
            best_provider = next(
                provider for provider, servers in DNS_PROVIDERS.items()
                if best_server in servers
            )
            self.dns_combo.set(best_provider)
            self.update_dns_field()
            messagebox.showinfo("Результат", f"Лучший DNS: {best_provider} ({best_time:.2f} мс)")
        else:
            messagebox.showerror("Ошибка", "Не удалось проверить DNS-серверы")

    def update_dns_field(self, event=None):
        provider = self.dns_combo.get()
        if provider == "Ручной ввод":
            self.manual_frame.grid(row=2, column=0, columnspan=2, pady=5)
            self.primary_entry.delete(0, tk.END)
            self.secondary_entry.delete(0, tk.END)
        else:
            self.manual_frame.grid_forget()
            primary, secondary = DNS_PROVIDERS[provider]
            self.primary_entry.delete(0, tk.END)
            self.primary_entry.insert(0, primary)
            self.secondary_entry.delete(0, tk.END)
            self.secondary_entry.insert(0, secondary)

    def check_admin(self):
        if not ctypes.windll.shell32.IsUserAnAdmin():
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit()

    def update_interfaces(self):
        try:
            interface = psutil.net_if_stats()
            active = [name for name, stats in interface.items() if stats.isup]
            self.interface_combo['values'] = active
            if active:
                self.interface_combo.current(0)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка получения интерфейсов: {str(e)}")

    def apply_dns(self):
        interface = self.interface_combo.get()
        primary = self.primary_entry.get()
        secondary = self.secondary_entry.get()

        if not interface:
            messagebox.showerror("Ошибка", "Выберите сетевой интерфейс!")
            return

        if not (primary and secondary):
            messagebox.showerror("Ошибка", "Заполните оба DNS-сервера!")
            return

        try:
           
            subprocess.run(f'netsh interface ipv4 delete dns "{interface}" all', 
                           shell=True, check=True, stderr=subprocess.PIPE, stdin=subprocess.PIPE)

         
            current_dns = subprocess.check_output(
                f'netsh interface ipv4 show dns "{interface}"',
                shell=True, stderr=subprocess.PIPE).decode('cp866', errors='ignore')

            if "не настроены" in current_dns or "No DNS servers configured" in current_dns:
                messagebox.showwarning("Внимание", "На этом компьютере не настроены DNS-серверы.")

          
            subprocess.run(f'netsh interface ipv4 set dns name="{interface}" static {primary}', 
                           shell=True, check=True, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
          
            subprocess.run(f'netsh interface ipv4 add dns name="{interface}" {secondary} index=2', 
                           shell=True, check=True, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            messagebox.showinfo("Успех", "DNS успешно изменены!")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('cp866', errors='ignore') if e.stderr else str(e)
            messagebox.showerror("Ошибка", f"Ошибка выполнения:\n{error_msg}")

    def reset_dns(self):
        interface = self.interface_combo.get()
        if not interface:
            messagebox.showerror("Ошибка", "Выберите сетевой интерфейс!")
            return

        try:
            subprocess.run(f'netsh interface ipv4 set dnsservers name="{interface}" source=dhcp', 
                           shell=True, check=True, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            messagebox.showinfo("Успех", "DNS сброшены к DHCP!")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('cp866', errors='ignore') if e.stderr else str(e)
            messagebox.showerror("Ошибка", f"Ошибка сброса:\n{error_msg}")

if __name__ == "__main__":
    root = tk.Tk()
    app = DNSChangerApp(root)
    root.mainloop()    
