# ChatGPT Telegram Bot
![python-version](https://img.shields.io/badge/python-3.9-blue.svg)
[![openai-version](https://img.shields.io/badge/openai-0.27.4-orange.svg)](https://openai.com/)
[![license](https://img.shields.io/badge/License-GPL%202.0-brightgreen.svg)](LICENSE)
[![Publish Docker image](https://github.com/n3d1117/chatgpt-telegram-bot/actions/workflows/publish.yaml/badge.svg)](https://github.com/n3d1117/chatgpt-telegram-bot/actions/workflows/publish.yaml)

OpenAI'nin _resmi_ [ChatGPT](https://openai.com/blog/chatgpt/), [DALL-E](https://openai.com/product/dall-e-2) ve [Whisper](https://openai.com/research/whisper) API'leriyle entegre olarak yanıtlar sağlayan bir [Telegram botu](https://core.telegram.org/bots/api). Minimum yapılandırma ile kullanıma hazırdır.

## Ekran Görüntüleri
![demo](https://user-images.githubusercontent.com/11541888/225114786-0d639854-b3e1-4214-b49a-e51ce8c40387.png)

## Özellikler
- [x] Yanıtlarda Markdown desteği.
- [x] Konuşmayı `/reset` komutu ile sıfırlama özelliği.
- [x] Yanıt oluşturulurken yazıyor işareti.
- [x] İzin verilen kullanıcıların bir listesi belirtilerek erişim kısıtlanabilir.
- [x] Docker ve Proxy desteği mevcuttur.
- [x] (YENİ!) `/image` komutu aracılığıyla DALL·E kullanarak resim oluşturma özelliği.
- [x] (YENİ!) Whisper kullanarak sesli ve videolu mesajları metne çevirme özelliği (ffmpeg gerekebilir).
- [x] (YENİ!) Fazla token kullanımını önlemek için otomatik konuşma özeti.
- [x] (YENİ!) Kullanıcı başına token kullanım takibi - @AlexHTW tarafından.
- [x] (YENİ!) `/stats` komutu aracılığıyla kişisel token kullanım istatistikleri ve günlük/aylık maliyet bilgileri alma - @AlexHTW tarafından 
- [x] (YENİ!) Kullanıcı bütçeleri ve misafir bütçeleri desteği - @AlexHTW tarafından.
- [x] (YENİ!) Akış desteği.
- [x] (YENİ!) GPT-4 desteği.
 -GPT-4 API'ye erişiminiz varsa, `OPENAI_MODEL` parametresini `gpt-4` olarak değiştirmeniz yeterlidir.
- [x] (YENİ!) Yerelleştirilmiş bot dili desteği.
 -Kullanılabilir diller :gb: :de: :ru: :tr: :it: :es: :indonesia: :netherlands: :cn: :vietnam:
- [x] (YENİ!) Grup ve özel sohbetlerde geliştirilmiş satır içi sorgu desteği - @bugfloyd tarafından.
 -Bu özelliği kullanmak için, BotFather'da `/setinline` komutu aracılığıyla botunuza satır içi sorgu(inline queries) özelliğini etkinleştirmeniz gerekmektedir.

## Ek özellikler - yardıma ihtiyaç var!
Eğer yardım etmek isterseniz, [issues](https://github.com/n3d1117/chatgpt-telegram-bot/issues) bölümüne göz atın ve katkıda bulunun!
Çevirilere yardımcı olmak istiyorsanız, [Translations Manual](https://github.com/n3d1117/chatgpt-telegram-bot/discussions/219)'a göz atın 

PR'larınızı(Pull request) her zaman bekliyoruz!

## Ön Gereklilikler
- Python 3.9+
- Bir [Telegram botu](https://core.telegram.org/bots#6-botfather) ve token'i (bkz. [öğretici](https://core.telegram.org/bots/tutorial#obtain-your-bot-token))
- Bir [OpenAI](https://openai.com) hesabı (bkz. [Konfigürasyon](#Konfigürasyon) bölümü)

## Başlarken

### Konfigürasyon
`.env.example` dosyasını kopyalayıp `.env` olarak yeniden adlandırarak yapılandırmayı özelleştirin ve ardından gerekli parametreleri istediğiniz gibi düzenleyin:

| Parametre                   | Açıklama                                                                                                                                                                                                                   |
|-----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `OPENAI_API_KEY`            | OpenAI key'iniz, [buradan](https://platform.openai.com/account/api-keys) alabilirsiniz                                                                                                                                 |
| `TELEGRAM_BOT_TOKEN`        | Telegram botunuzun token'i, [BotFather](http://t.me/botfather) kullanarak alabilirsiniz. (bkz. [öğretici](https://core.telegram.org/bots/tutorial#obtain-your-bot-token))                                                                  |
| `ADMIN_USER_IDS`            | Adminlerin kullanıcı ID'leri. Bu kullanıcılar spesifik komutlara erişebilirler, bilgi ve bütçe kısıtlamaları yoktur. Yönetici ID'lerinin `ALLOWED_TELEGRAM_USER_IDS`'a eklenmesi gerekmez. **Not**: Varsayılan olarak, admin yoktur (`-`) |
| `ALLOWED_TELEGRAM_USER_IDS` | Botla etkileşime girmesine izin verilen Telegram kullanıcı kimliklerinin virgülle ayrılmış bir listesi (kullanıcı kimliklerini bulmak için [getidsbot](https://t.me/getidsbot) kullanın). **Not**: varsayılan olarak *herkese* izin verilir (`*`) |

### İsteğe Bağlı Konfigürasyon
Aşağıdaki parametreler isteğe bağlıdır ve `.env` dosyasında ayarlanabilir:

#### Bütçeler   
| Parametre             | Açıklama                                                                                                                                                                                                                                                                                                                                                                               | Varsayılan değer      |
|-----------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------|
| `BUDGET_PERIOD`       | Tüm bütçelerin uygulanacağı zaman dilimini belirler. Kullanılabilir dönemler: `daily` *(bütçeyi her gün sıfırlar)*, `monthly` *(bütçeleri her ayın ilk günü sıfırlar)*, `all-time` *(bütçeyi asla sıfırlamaz)*. Daha fazla bilgi için [Bütçe Kılavuzu](https://github.com/n3d1117/chatgpt-telegram-bot/discussions/184)'na bakın                                                                  | `monthly`          |
| `USER_BUDGETS`        | `ALLOWED_TELEGRAM_USER_IDS` listesindeki her kullanıcı için özelleştirilmiş OpenAI API maliyet sınırı belirlemek için kullanılan, virgülle ayrılmış $ tutarları listesi. Kullanıcı listeleri için her kullanıcıya ilk `USER_BUDGETS` değeri verilir. **Not**: varsayılan olarak, herhangi bir kullanıcı için *sınır yoktur* (`*`). Daha fazla bilgi için [Bütçe Kılavuzu](https://github.com/n3d1117/chatgpt-telegram-bot/discussions/184)'na bakın | `*`                |
| `GUEST_BUDGET`        | Tüm misafir kullanıcılar için $ bazında kullanım sınırı. Misafir kullanıcılar, grup sohbetlerinde `ALLOWED_TELEGRAM_USER_IDS` listesinde olmayan kullanıcılardır. Kullanıcı bütçelerinde herhangi bir kullanım sınırı belirlenmemişse değer yok sayılır (`USER_BUDGETS`=`*`). Daha fazla bilgi için [Bütçe Kılavuzu](https://github.com/n3d1117/chatgpt-telegram-bot/discussions/184)'na bakın                                                    | `100.0`            |
| `TOKEN_PRICE`         | Kullanım istatistiklerinde maliyet bilgilerini hesaplamak için kullanılan 1000 jeton başına düşen $ fiyatı. Kaynak: https://openai.com/pricing                                                                                                                                                                                                                                                                          | `0.002`            |
| `IMAGE_PRICES`        | Farklı görüntü boyutları için 3 öğeden oluşan virgülle ayrılmış fiyatlar listesi: 256x256, 512x512 ve 1024x1024. Kaynak: https://openai.com/pricing                                                                                                                                                                                                                                  | `0.016,0.018,0.02` |
| `TRANSCRIPTION_PRICE` | Bir dakikalık ses transkripsiyonu için $ cinsinden fiyat. Kaynak: https://openai.com/pricing                                                                                                                                                                                                                                                                                                       | `0.006`            |

Olası bütçe yapılandırmaları için [Bütçe Kılavuzu](https://github.com/n3d1117/chatgpt-telegram-bot/discussions/184)'na göz atın.

#### İsteğe bağlı ek yapılandırma seçenekleri
| Parametre                          | Açıklama                                                                                                                                                                                                                    | Varsayılan değer                      |
|------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------|
| `ENABLE_QUOTING`                   | Özel sohbetlerde mesaj alıntılamanın etkinleştirilip etkinleştirilmeyeceği                                                                                                                                                                             | `true`                             |
| `ENABLE_IMAGE_GENERATION`          | Görüntü üretiminin `/image` komutu aracılığıyla etkinleştirilip etkinleştirilmeyeceği                                                                                                                                                                    | `true`                             |
| `ENABLE_TRANSCRIPTION`             | Sesli ve video'lu mesajların sesten yazıya çeviri özelliğinin etkinleştirilip etkinleştirilmeyeceği                                                                                                                                                                   | `true`                             |
| `PROXY`                            | OpenAI ve Telegram botu için kullanılacak proxy (örn. `http://localhost:8080`)                                                                                                                                                    | -                                  |
| `OPENAI_MODEL`                     | Yanıt üretmek için kullanılacak OpenAI modeli                                                                                                                                                                               | `gpt-3.5-turbo`                    |
| `ASSISTANT_PROMPT`                 | Tonu belirleyen ve asistanın davranışını kontrol eden bir sistem mesajı                                                                                                                                                 | `You are a helpful assistant.`     |
| `SHOW_USAGE`                       | Her yanıttan sonra OpenAI token kullanım bilgilerinin gösterilip gösterilmeyeceği                                                                                                                                                             | `false`                            |
| `STREAM`                           | Yanıtların akış şeklinde verilmesi. **Not**: etkinleştirilmişse, `N_CHOICES` 1'den büyükse çalışmaz                                                                                                                                | `true`                             |
| `MAX_TOKENS`                       | ChatGPT API'sinin kaç jeton döndüreceğine ilişkin üst sınır                                                                                                                                                                     | GPT-3 için `1200`, GPT-4 için `2400` |
| `MAX_HISTORY_SIZE`                 | Bellekte tutulacak maksimum mesaj sayısı, belirlenen değerden sonra aşırı belirteç kullanımını önlemek için konuşma özetlenecektir                                                                                                       | `15`                               |
| `MAX_CONVERSATION_AGE_MINUTES`     | Bir görüşmenin son mesajdan bu yana aktif kalması gereken maksimum dakika sayısı; bu süreden sonra görüşme sıfırlanır                                                                                                        | `180`                              |
| `VOICE_REPLY_WITH_TRANSCRIPT_ONLY` | Sesli mesajların yazıya çevirildikten sonra ChatGPT ile yanıt verilip verilmeyeceği (Eğer false olarak seçilirse sesli mesaj çevirildikten sonra ChatGPT tarafından cevaplanır)                                                                                                                      | `false`                            |
| `VOICE_REPLY_PROMPTS`              | Noktalı virgülle ayrılmış ifadeler listesi (örn. `Hey bot;Merhaba bot`). Transkript bunlardan herhangi biriyle başlarsa, `VOICE_REPLY_WITH_TRANSCRIPT_ONLY` `true` olarak ayarlanmış olsa bile bir komut olarak değerlendirilecektir.                        | -                                  |
| `N_CHOICES`                        | Her girdi mesajı için üretilecek cevap sayısı. **Not**: `STREAM` etkinleştirilmişse bunu 1'den büyük bir sayıya ayarlamak düzgün çalışmamasına sebep olacaktır                                                                           | `1`                                |
| `TEMPERATURE`                      | 0 ile 2 arasında bir sayı. Daha yüksek değerler çıktıyı daha rastgele hale getirecektir                                                                                                                                                         | `1.0`                              |
| `PRESENCE_PENALTY`                 |  -2.0 ile 2.0 arasında değerler verilebilir. Pozitif değer verildiğinde bir sonraki kelimenin metinle ilişkili olmasına dikkat edilir. Örneğin "Ben bir ..." cümlesi için; ayar pozitif bir değer ise, model daha önce metinde geçen kelimelere daha fazla ağırlık verir ve bu, örneğin "yazarım" yerine "öğrenciyim" kelimesinin daha yüksek bir olasılıkla önerilmesine neden olabilir.                                                                                                                  | `0.0`                              |
| `FREQUENCY_PENALTY`                | -2.0 ile 2.0 arasında değerler verilebilir. Pozitif değer verildiğinde sık kullanılan kelimelere daha az ağırlık verilir                                                                                                          | `0.0`                              |
| `IMAGE_SIZE`                       | DALL-E tarafından oluşturulan görüntü boyutu. İzin verilen değerler: `256x256`, `512x512` veya `1024x1024`                                                                                                                                           | `512x512`                          |
| `GROUP_TRIGGER_KEYWORD`            | Ayarlanırsa, grup sohbetlerindeki bot yalnızca bu anahtar sözcükle başlayan mesajlara yanıt verir                                                                                                                                      | -                                  |
| `IGNORE_GROUP_TRANSCRIPTIONS`      | true olarak ayarlanırsa, bot grup sohbetlerindeki sesten yazıya çevirme işlemlerini gerçekleştirmez                                                                                                                                                         | `true`                             |
| `BOT_LANGUAGE`                     | Genel bot mesajlarının dili. Şu anda mevcut olan diller: `en`, `de`, `ru`, `tr`, `it`, `es`, `id`, `nl`, `cn`, `vi`.  [Ek çevirilerle katkıda bulunun](https://github.com/n3d1117/chatgpt-telegram-bot/discussions/219) | `en`                               |

Daha fazla ayrıntı için, [resmi API referansına](https://platform.openai.com/docs/api-reference/chat) bakabilirsiniz

### Kurulum
Depoyu klonlayın ve proje dizinine gidin:

```shell
git clone https://github.com/n3d1117/chatgpt-telegram-bot.git
cd chatgpt-telegram-bot
```

#### Kaynak Koddan Kurulum İçin: 
1. Sanal ortamı oluşturun:
```shell
python -m venv venv
```

2. Sanal ortamı etkinleştirin:
```shell
# Linux veya macOS için:
source venv/bin/activate

# Windows için:
venv\Scripts\activate
```

3. requirements.txt'i kullanarak gereksinimleri kurun:
```shell
pip install -r requirements.txt
```

4. Bot'u başlatmak için aşağıdaki komutu kullanın:
```
python bot/main.py
```

#### Docker Compose kullanarak:

Docker imajını oluşturmak ve çalıştırmak için aşağıdaki komutu kullanın:
```shell
docker compose up
```

#### Kullanıma hazır Docker imajları
Docker görüntüsünü [Docker Hub](https://hub.docker.com/r/n3d1117/chatgpt-telegram-bot) adresinden de kullanabilirsiniz:
```shell
docker pull n3d1117/chatgpt-telegram-bot:latest
```

veya [GitHub Container Registry](https://github.com/n3d1117/chatgpt-telegram-bot/pkgs/container/chatgpt-telegram-bot/) kullanarak:

```shell
docker pull ghcr.io/n3d1117/chatgpt-telegram-bot:latest
```

## Kullanılan Kaynaklar
- [ChatGPT](https://chat.openai.com/chat) from [OpenAI](https://openai.com)
- [python-telegram-bot](https://python-telegram-bot.org)
- [jiaaro/pydub](https://github.com/jiaaro/pydub)

## Uyarı
Bu bir kişisel proje olup hiçbir şekilde OpenAI ile bağlantılı değildir.

## Lisans
Bu proje GPL 2.0 lisansı şartları altında yayınlanmıştır. Daha fazla bilgi için, depoya dahil edilen [LICENSE](LICENSE) dosyasına bakın.