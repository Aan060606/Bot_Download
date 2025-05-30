import re, json, requests
from bs4 import BeautifulSoup as bs
from concurrent.futures import ThreadPoolExecutor

class PoopScraper: # Mengganti nama kelas menjadi PoopScraper agar lebih deskriptif dan menghindari konflik nama

    #--> konstruktor
    def __init__(self) -> None:

        self.r    = requests.Session()
        self.url  = None
        self.host = None

        self.data_file : list = []
        self.result    : dict = {
            'status' : 'failed',
            'data'   : self.data_file,
        }

    #--> redirect karena domain berubah-ubah
    def redirect(self, url:str) -> None:
        try:
            response = self.r.get(url, allow_redirects=True, timeout=10) # Tambahkan timeout
            self.url = response.url
            self.host = 'https://{}/'.format(self.url.split('/')[2])
        except Exception as e:
            # print(f"Error in redirect: {e}") # Untuk debugging, bisa dihapus di produksi
            pass

    #--> landing, buat sortir tipe data yang dikirim dari client (str/list)
    def execute(self, raw_url:str|list) -> None:
        self.data_file = [] # Reset data_file untuk setiap eksekusi baru
        self.result['data'] = self.data_file

        if isinstance(raw_url, list):
            with ThreadPoolExecutor(max_workers=5) as TPE: # Kurangi max_workers untuk menghindari blocking
                futures = [TPE.submit(self.get_file, i) for i in raw_url]
                # Opsional: tunggu semua future selesai jika Anda butuh hasil yang terurut atau menangani kesalahan
                for future in futures:
                    future.result() # Ini akan memunculkan exception jika ada
        elif isinstance(raw_url, str):
            self.get_file(raw_url)

        if len(self.data_file) > 0:
            self.result['status'] = 'success'
        else:
            self.result['status'] = 'failed' # Pastikan status failed jika tidak ada data

    #--> main method
    def get_file(self, url:str):

        #--> cek apakah url valid
        self.redirect(url)
        if not self.host: return

        #--> cek tipe url
        url_type : str = self.url.split('/')[3].lower()

        if url_type == 'f': #--> folder
            id_folder = self.url.split('/')[4]
            self.get_data_multi_file(id_folder)

        elif url_type == 'd' or url_type == 'e' or url_type == 'v': #--> file, 'v' juga mungkin link video
            id_file = self.url.split('/')[4]
            self.get_data_single_file(id_file)

    #--> dapetin semua id_file dari folder
    def get_data_multi_file(self, id_folder:str) -> None:
        try:
            url : str = f'{self.host}f/{id_folder}'
            response : object = self.r.get(url, headers={'referer':self.host}, allow_redirects=False, timeout=10)
            response.raise_for_status() # Cek status HTTP
            response_bs4 : str = bs(response.content, 'html.parser')

            find_a = response_bs4.find_all('a', {'href':True, 'class':'title_video'})
            list_id_file = [re.search(r'href="(.*?)"',str(item)).group(1).split('/')[-1] for item in find_a]

            if len(list_id_file):
                with ThreadPoolExecutor(max_workers=5) as TPE: # Kurangi max_workers
                    futures = [TPE.submit(self.get_data_single_file, id_file) for id_file in list_id_file]
                    for future in futures:
                        future.result()
        except Exception as e:
            # print(f"Error in get_data_multi_file: {e}")
            pass

    #--> dapetin data tiap file
    def get_data_single_file(self, id_file:str) -> None:
        packed_data = {
            'id' : id_file,
            **self.get_file_information(id_file), #--> ambil informasi suatu file (ukuran, waktu, dll)
            **self.get_thumbnail_and_video_url(id_file), #--> ambil url gambar & video
        }

        # Pastikan semua kunci yang diharapkan ada dan tidak None
        required_keys = ['filename', 'size', 'duration', 'thumbnail_url', 'video_url']
        if all(packed_data.get(k) is not None for k in required_keys):
             self.data_file.append(packed_data)
        # else:
            # print(f"Skipping incomplete data for {id_file}: {packed_data}") # Untuk debugging

    #--> dapetin informasi dari file (ukuran, waktu, dll)
    def get_file_information(self, id_file:str) -> dict[str,str|int]:
        file_name, file_size, file_duration, file_upload_date = None, None, None, None
        try:
            url : str = f'{self.host}d/{id_file}'
            response : object = self.r.get(url, headers={'referer':self.host}, allow_redirects=False, timeout=10)
            response.raise_for_status()
            response_bs4 : str = bs(response.content, 'html.parser')

            find_div = response_bs4.find('div', {'class':'info'})
            if find_div:
                file_name_tag = find_div.find('h4')
                file_size_tag = find_div.find('div', {'class':'size'})
                file_duration_tag = find_div.find('div', {'class':'length'})
                file_upload_date_tag = find_div.find('div', {'class':'uploadate'})

                if file_name_tag: file_name = file_name_tag.text.strip()
                if file_size_tag: file_size = file_size_tag.text.strip()
                if file_duration_tag: file_duration = file_duration_tag.text.strip()
                if file_upload_date_tag: file_upload_date = file_upload_date_tag.text.strip()
        except Exception as e:
            # print(f"Error in get_file_information for {id_file}: {e}")
            pass

        return({
            'filename'      : file_name,
            'size'          : file_size,
            'duration'      : file_duration,
            'upload_date'   : file_upload_date,
        })

    #--> dapetin url gambar & video
    def get_thumbnail_and_video_url(self, id_file:str) -> dict[str,str]:
        thumbnail_url, video_url = None, None
        try:
            url : str = f'https://poophd.video-src.com/vplayer?id={id_file}'
            response : object = self.r.get(url, headers={'referer':self.host}, allow_redirects=False, timeout=10)
            response.raise_for_status()
            response_text : str = response.text.replace('\\','')

            raw_match : str = re.search(r'player\((.*?)\);',response_text)
            if raw_match:
                match_group = raw_match.group(1)
                match : tuple = eval(f'({match_group})')
                if len(match) >= 2: # Pastikan ada cukup elemen
                    thumbnail_url = match[1].replace(' ','%20')
                    if len(match) >= 3: # Video URL biasanya elemen terakhir, tapi amankan
                        video_url = match[-1].replace(' ','%20')

                    try:
                        # Perbaikan: jika domain thumbnail berbeda dari domain video, gunakan domain video
                        match_old = re.search(r'https://(.*?)/',thumbnail_url)
                        match_new = re.search(r'https://(.*?)/',video_url)
                        if match_old and match_new:
                            thumbnail_url = thumbnail_url.replace(match_old.group(1), match_new.group(1))
                    except Exception:
                        pass # Tidak masalah jika penggantian domain gagal
            else:
                # Coba regex lain jika format 'player()' tidak ditemukan
                video_url_match = re.search(r'file:[\'"](https?://[^\'"]+\.mp4)[\'"]', response_text)
                if video_url_match:
                    video_url = video_url_match.group(1).replace(' ','%20')
                
                thumbnail_url_match = re.search(r'image:[\'"](https?://[^\'"]+\.(?:jpg|png|gif))[\'"]', response_text)
                if thumbnail_url_match:
                    thumbnail_url = thumbnail_url_match.group(1).replace(' ','%20')

        except Exception as e:
            # print(f"Error in get_thumbnail_and_video_url for {id_file}: {e}")
            pass

        return({
            'thumbnail_url' : thumbnail_url,
            'video_url'     : video_url,
        })

# if __name__ == '__main__':
#     poop = PoopScraper()

#     # Test 1 file
#     print("Testing single file:")
#     url_single = 'https://poophd.pro/d/aj4exwdptytk'
#     poop.execute(url_single)
#     print(json.dumps(poop.result, indent=4))
#     print("-" * 50)

#     # Test 1 folder
#     print("Testing single folder:")
#     url_folder = 'https://poop.vision/f/191hxk2iul2'
#     poop.execute(url_folder)
#     print(json.dumps(poop.result, indent=4))
#     print("-" * 50)

#     # Test multiple folders/files (from the list you provided)
#     print("Testing multiple URLs:")
#     urls_list = [
#         'https://poop.vin/f/UUbQBNXiuki',
#         'https://poop.vin/f/rehBVh38rx3',
#         'https://poop.vin/d/aj4exwdptytk', # Tambahkan contoh file tunggal
#         'https://poop.vision/f/191hxk2iul2' # Contoh folder lain
#     ]
#     poop.execute(urls_list)
#     print(json.dumps(poop.result, indent=4))
#     print("-" * 50)