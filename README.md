# DuckDNS Güncelleme Aracı (Python GUI)

Bu proje, DuckDNS dinamik DNS servisini otomatik olarak güncelleyen, hem Windows hem Linux üzerinde çalışan, Python tabanlı grafiksel arayüze sahip bir uygulamadır.

---

## Özellikler

- DuckDNS domain ve token bilgilerini GUI üzerinden kolayca girip kaydetme  
- Güncelleme işlemini manuel olarak başlatma  
- Saatlik otomatik güncelleme  
- Son güncelleme zamanını ve aktif ağ arayüzünü gösterme  
- Uygulama simgesi sistem tepsisinde gizlenir, minimize edildiğinde arka planda çalışmaya devam eder  
- Güncelleme durumlarını renkli log penceresinde gösterir (başarılı = yeşil, hata = kırmızı)  
- Windows kullanıcıları için programı `.exe` haline dönüştürme butonu  
- Aynı anda sadece bir instance çalışmasına izin verir  

---

## Gereksinimler

- Python 3.7 ve üzeri  
- Gerekli Python kütüphaneleri:

```bash
pip install pyqt5 pystray pillow requests psutil
