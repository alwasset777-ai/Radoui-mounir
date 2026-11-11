# -*- coding: utf-8 -*-
"""
✨ فيديو بالذكاء الاصطناعي — نسخة شخصية فابور 100% (بلا جواهر، بلا اشتراك)
- صورة إلى فيديو  /  نص إلى فيديو
- الموديل: Wan 2.2 TI2V-5B (مفتوح، رخصة Apache 2.0) على GPU فابور ديال Kaggle
- المدة الطويلة: قطع ديال 5 ثواني كتتلصق (كل قطعة كتبدا من آخر لقطة ديال اللي قبلها)
- الرابط الثابت: كيتصيفط أوتوماتيكياً لصفحة ntfy (إشعار فالتليفون)
"""
import os
import re
import sys
import time
import uuid
import queue
import random
import shutil
import datetime
import threading
import traceback
import subprocess

import numpy as np
from PIL import Image, ImageOps

# ----------------------------------------------------------------------------
# الإعدادات
# ----------------------------------------------------------------------------
MODEL_ID = os.environ.get("WAN_MODEL_ID", "Wan-AI/Wan2.2-TI2V-5B-Diffusers")
ON_KAGGLE = os.path.isdir("/kaggle/working")
OUT_DIR = os.environ.get(
    "VIDEO_OUT_DIR", "/kaggle/working/videos" if ON_KAGGLE else os.path.abspath("videos")
)
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
IDLE_MINUTES = float(os.environ.get("IDLE_MINUTES", "60"))  # كيطفى بوحدو إلا بقى خاوي باش توفر الساعات
PORT = int(os.environ.get("PORT", "7860"))
FPS = 24
SEG_FRAMES = int(os.environ.get("SEG_FRAMES", "121"))  # 121 لقطة = 5 ثواني
SEG_SECONDS = (SEG_FRAMES - 1) / FPS
MAX_SEQ = 512
DURATIONS = [5, 10, 15, 20, 30, 45, 60]

ASPECTS = ["عمودي 9:16", "أفقي 16:9", "مربع 1:1"]
Q_HIGH, Q_FAST = "عالية (720p)", "سريعة (480p)"
QUALITY = {
    Q_HIGH: {
        "area": 704 * 1280,
        "steps": 35,
        "sizes": {"عمودي 9:16": (704, 1280), "أفقي 16:9": (1280, 704), "مربع 1:1": (960, 960)},
    },
    Q_FAST: {
        "area": 480 * 832,
        "steps": 30,
        "sizes": {"عمودي 9:16": (480, 832), "أفقي 16:9": (832, 480), "مربع 1:1": (640, 640)},
    },
}
MOD = 32

NEG_PROMPT = (
    "色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，"
    "JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，"
    "形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走，"
    "裸露，色情，nsfw, nudity"
)
DEFAULT_PROMPT = "Natural smooth motion, gentle cinematic camera movement, realistic lighting, high quality, detailed"
NO_GPU_MSG = "❌ ما كاينش GPU. فـ Kaggle: Settings ← Accelerator ← «GPU T4 x2»، ومن بعد عاود."

STATE = {"url": None, "last_activity": time.time()}


def log(*a):
    print(datetime.datetime.now().strftime("%H:%M:%S"), *a, flush=True)


def touch():
    STATE["last_activity"] = time.time()


# ----------------------------------------------------------------------------
# إشعارات فالتليفون (ntfy.sh — فابور بلا حساب)
# ----------------------------------------------------------------------------
def notify(title, message, click=None, tags=None, priority=3):
    if not NTFY_TOPIC:
        return False
    body = {"topic": NTFY_TOPIC, "title": title, "message": message, "priority": priority, "tags": tags or []}
    if click:
        body["click"] = click
        body["actions"] = [{"action": "view", "label": "افتح التطبيق", "url": click}]
    try:
        import requests

        r = requests.post(os.environ.get("NTFY_SERVER", "https://ntfy.sh/"), json=body, timeout=15)
        return r.ok
    except Exception as e:
        log("notify failed:", e)
        return False


# ----------------------------------------------------------------------------
# أدوات صغيرة
# ----------------------------------------------------------------------------
def size_from_image(img, area):
    ratio = img.height / img.width
    h = int(round(np.sqrt(area * ratio)) // MOD * MOD)
    w = int(round(np.sqrt(area / ratio)) // MOD * MOD)
    return max(MOD, w), max(MOD, h)


def fit_image(img, w, h):
    return ImageOps.fit(img.convert("RGB"), (w, h), method=Image.LANCZOS, centering=(0.5, 0.5))


def match_color(img, ref, strength=0.5):
    try:
        import cv2
    except ImportError:
        return img
    a = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2LAB).astype(np.float32)
    r = cv2.cvtColor(np.asarray(ref.convert("RGB")), cv2.COLOR_RGB2LAB).astype(np.float32)
    am, asd = a.reshape(-1, 3).mean(0), a.reshape(-1, 3).std(0) + 1e-5
    rm, rsd = r.reshape(-1, 3).mean(0), r.reshape(-1, 3).std(0) + 1e-5
    out = (a - am) / asd * rsd + rm
    out = np.clip(a * (1 - strength) + out * strength, 0, 255).astype(np.uint8)
    return Image.fromarray(cv2.cvtColor(out, cv2.COLOR_LAB2RGB))


_tr_cache = {}


def to_english(text):
    if not re.search(r"[؀-ۿ]", text):
        return text
    if text in _tr_cache:
        return _tr_cache[text]
    try:
        from deep_translator import GoogleTranslator

        out = GoogleTranslator(source="auto", target="en").translate(text) or text
    except Exception as e:
        log("translation failed:", e)
        out = text
    _tr_cache[text] = out
    return out


def ffmpeg_exe():
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg") or "ffmpeg"


def write_mp4(frames_u8, path):
    import imageio.v2 as imageio

    w = imageio.get_writer(path, fps=FPS, codec="libx264", quality=8, pixelformat="yuv420p",
                           macro_block_size=1, ffmpeg_log_level="error")
    for f in frames_u8:
        w.append_data(f)
    w.close()


def concat_mp4(parts, out_path):
    if len(parts) == 1:
        shutil.copyfile(parts[0], out_path)
        return
    lst = out_path + ".txt"
    with open(lst, "w") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")
    tmp = out_path + ".tmp.mp4"
    subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", tmp], check=True)
    os.replace(tmp, out_path)
    os.remove(lst)


class Cancelled(Exception):
    pass


# ----------------------------------------------------------------------------
# المحرك
# ----------------------------------------------------------------------------
class Engine:
    def __init__(self):
        self.ready = False
        self.error = None
        self.status = "⏳ كيتوجد…"
        self._active = None
        self._emb = {}
        self.cuda = False

    def load(self, components=None):
        try:
            import torch
            from diffusers import WanImageToVideoPipeline, WanPipeline

            self.torch = torch
            self.t_load = time.time()
            if components is None:
                if not torch.cuda.is_available():
                    raise RuntimeError(NO_GPU_MSG)
                from diffusers import AutoencoderKLWan, UniPCMultistepScheduler, WanTransformer3DModel
                from transformers import AutoTokenizer, UMT5EncoderModel

                n_gpu = torch.cuda.device_count()
                self.status = "⏳ كنحمّل الموديل (أول مرة 5 حتى 15 دقيقة)…"
                log(self.status, f"GPUs={n_gpu}")
                tok = AutoTokenizer.from_pretrained(MODEL_ID, subfolder="tokenizer")
                # فهم النص: إلا كاين جوج GPU كنحطوه فالثاني (أسرع ويخفف الذاكرة)، وإلا فالـ CPU
                if n_gpu >= 2:
                    te = UMT5EncoderModel.from_pretrained(MODEL_ID, subfolder="text_encoder",
                                                          torch_dtype=torch.float16).to("cuda:1")
                else:
                    te = UMT5EncoderModel.from_pretrained(MODEL_ID, subfolder="text_encoder",
                                                          torch_dtype=torch.bfloat16)
                self.status = "⏳ كنحمّل الجزء الكبير ديال الموديل…"
                tr = WanTransformer3DModel.from_pretrained(MODEL_ID, subfolder="transformer", torch_dtype=torch.float16)
                vae = AutoencoderKLWan.from_pretrained(MODEL_ID, subfolder="vae", torch_dtype=torch.float32)
                sch = UniPCMultistepScheduler.from_pretrained(MODEL_ID, subfolder="scheduler")
                components = dict(tokenizer=tok, text_encoder=te, transformer=tr, vae=vae, scheduler=sch)

            self.tokenizer = components["tokenizer"]
            self.text_encoder = components["text_encoder"].eval()
            self.vae = components["vae"]
            common = dict(
                tokenizer=components["tokenizer"], text_encoder=None, vae=components["vae"],
                scheduler=components["scheduler"], transformer=components["transformer"],
                transformer_2=None, boundary_ratio=None, expand_timesteps=True,
            )
            self.i2v = WanImageToVideoPipeline(image_processor=None, image_encoder=None, **common)
            _orig_prepare = self.i2v.prepare_latents

            def _prepare_then_free_vae(*a, **k):
                out = _orig_prepare(*a, **k)
                if torch.cuda.is_available():
                    self.vae.to("cpu")  # كيرجع بوحدو للـ GPU ملي نحتاجوه فالأخير
                    torch.cuda.empty_cache()
                return out

            self.i2v.prepare_latents = _prepare_then_free_vae
            self.t2v = WanPipeline(**common)
            for p in (self.i2v, self.t2v):
                p.set_progress_bar_config(disable=True)
            self.cuda = torch.cuda.is_available()
            self.embed(NEG_PROMPT)  # كنجربو فهم النص من دابا
            self.status = "⏳ كنجرب الموديل بفيديو صغير…"
            self.self_test()
            self.ready = True
            touch()  # عداد الإطفاء كيبدا من دابا، ماشي من وقت التحميل
            self.status = "✅ واجد"
            log("model ready")
            notify("✅ التطبيق واجد", "الموديل تحمّل، تقدر تصاوب الفيديوهات دابا.", STATE["url"], ["white_check_mark"])
        except Exception as e:
            self.error = str(e)
            self.status = f"❌ مشكل فتحميل الموديل: {e}"
            log(self.status)
            traceback.print_exc()
            notify("❌ مشكل فالتطبيق", self.status[:300], None, ["x"], 4)

    def _encode(self, text):
        torch = self.torch
        from diffusers.pipelines.wan.pipeline_wan import prompt_clean

        dev = next(self.text_encoder.parameters()).device
        inputs = self.tokenizer([prompt_clean(text)], padding="longest", max_length=MAX_SEQ, truncation=True,
                                add_special_tokens=True, return_attention_mask=True, return_tensors="pt")
        with torch.no_grad():
            h = self.text_encoder(inputs.input_ids.to(dev), inputs.attention_mask.to(dev)).last_hidden_state
        n = int(inputs.attention_mask.gt(0).sum())
        return h[0, :n].float().cpu()

    def embed(self, text):
        torch = self.torch
        if text in self._emb:
            return self._emb[text]
        h = self._encode(text)
        if not torch.isfinite(h).all():  # احتياط: إلا فشل فالـ GPU كنرجعو للـ CPU
            log("text encoder gave NaN → moving to CPU bf16")
            self.text_encoder = self.text_encoder.to("cpu", torch.bfloat16)
            h = self._encode(text)
        h = torch.cat([h, h.new_zeros(MAX_SEQ - h.size(0), h.size(1))])[None]
        self._emb[text] = h
        return h

    def _use(self, pipe):
        if self.cuda and self._active is not pipe:
            pipe.enable_model_cpu_offload(gpu_id=0)
            self._active = pipe

    def _decode(self, latents):
        torch = self.torch
        from diffusers.utils.torch_utils import get_module_execution_device

        vae = self.vae
        lat = latents.to(device=get_module_execution_device(vae), dtype=vae.dtype)
        mean = torch.tensor(vae.config.latents_mean).view(1, vae.config.z_dim, 1, 1, 1).to(lat.device, lat.dtype)
        std = 1.0 / torch.tensor(vae.config.latents_std).view(1, vae.config.z_dim, 1, 1, 1).to(lat.device, lat.dtype)
        lat = lat / std + mean
        with torch.no_grad():
            try:
                video = vae.decode(lat, return_dict=False)[0]
            except torch.cuda.OutOfMemoryError:
                log("decode OOM → retry with tiling")
                torch.cuda.empty_cache()
                vae.enable_tiling()
                video = vae.decode(lat, return_dict=False)[0]
        frames = self.i2v.video_processor.postprocess_video(video, output_type="np")[0]
        return (np.clip(frames, 0, 1) * 255).round().astype(np.uint8)

    def to_bf16(self):
        """إلا الموديل عطى نتيجة خاوية (NaN) بدقة fp16، كنبدلوه لـ bf16 (أبطأ شوية ولكن أضمن)."""
        torch = self.torch
        tr = self.i2v.transformer
        if tr.dtype == torch.bfloat16:
            return False
        log("fp16 gave NaN → switching transformer to bf16")
        for p in (self.i2v, self.t2v):
            try:
                p.remove_all_hooks()
            except Exception:
                pass
        # نفس القاعدة ديال diffusers: شي أجزاء حساسة كتبقى بدقة كاملة (float32)
        keep = getattr(tr, "_keep_in_fp32_modules", None) or []
        with torch.no_grad():
            for name, t in list(tr.named_parameters()) + list(tr.named_buffers()):
                if t.is_floating_point():
                    t.data = t.data.float() if any(m in name for m in keep) else t.data.to(torch.bfloat16)
        self._active = None
        if self.cuda:
            torch.cuda.empty_cache()
        return True

    def self_test(self):
        """فيديو صغير (9 لقطات) كنتأكدو بيه بلي كلشي خدام قبل ما نقولو «واجد»."""
        for attempt in range(2):
            try:
                frames = self.segment(DEFAULT_PROMPT, None, 256, 256, 2, 5.0, 0, lambda s: None, num_frames=9)
                assert frames.shape[0] == 9
                log("self-test OK", frames.shape)
                return
            except RuntimeError as e:
                if "NAN_RESULT" in str(e) and attempt == 0 and self.to_bf16():
                    continue
                raise

    def segment(self, prompt_en, image, w, h, steps, guidance, seed, on_step, num_frames=None):
        torch = self.torch
        pipe = self.t2v if image is None else self.i2v
        self._use(pipe)
        dev = pipe._execution_device
        dt = pipe.transformer.dtype
        pe = self.embed(prompt_en).to(dev, dt)
        ne = self.embed(NEG_PROMPT).to(dev, dt)

        def cb(p, i, t, kw):
            on_step(i + 1)
            return kw

        kwargs = dict(
            prompt_embeds=pe, negative_prompt_embeds=ne, height=h, width=w, num_frames=num_frames or SEG_FRAMES,
            num_inference_steps=steps, guidance_scale=guidance,
            generator=torch.Generator(device="cpu").manual_seed(int(seed)),
            output_type="latent", callback_on_step_end=cb,
        )
        if image is not None:
            kwargs["image"] = image
        with torch.no_grad():
            latents = pipe(**kwargs).frames
        if not torch.isfinite(latents).all():
            raise RuntimeError("NAN_RESULT")
        frames = self._decode(latents)
        if self.cuda:
            torch.cuda.empty_cache()
        return frames


ENGINE = Engine()


# ----------------------------------------------------------------------------
# الطلبات (كتخدم فالخلفية)
# ----------------------------------------------------------------------------
class Job:
    def __init__(self, **kw):
        self.id = datetime.datetime.now().strftime("%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        self.__dict__.update(kw)
        self.state = "queued"
        self.seg_i = 0
        self.step = 0
        self.msg = "فاللائحة…"
        self.out = None
        self.cancel = False
        self.sec_per_step = None
        self.done_steps = 0


JOBS = []
LAST = {}  # آخر إعدادات تصيفطو (باش نعاودو بيهم)
Q = queue.Queue()


def run_job(job):
    job.state = "running"
    folder = os.path.join(OUT_DIR, "parts", job.id)
    os.makedirs(folder, exist_ok=True)
    final = os.path.join(OUT_DIR, f"video_{job.id}.mp4")
    parts = []
    q = QUALITY[job.quality]
    image = None
    if job.image is not None:
        img = ImageOps.exif_transpose(job.image).convert("RGB")
        w, h = size_from_image(img, q["area"])
        image = fit_image(img, w, h)
    else:
        w, h = q["sizes"][job.aspect]
    first_frame = image
    prompts_en = [to_english(p) if job.translate else p for p in job.prompts]
    job.w, job.h = w, h
    denoise_time = 0.0

    for i in range(job.n_seg):
        if job.cancel:
            raise Cancelled()
        job.seg_i = i + 1
        job.step = 0
        prompt = prompts_en[min(i, len(prompts_en) - 1)]
        job.msg = f"كنصاوب القطعة {i + 1} من {job.n_seg}"
        log(f"[{job.id}] seg {i + 1}/{job.n_seg} {w}x{h} prompt={prompt[:80]!r}")
        t_seg = time.time()

        def on_step(s, _t=[time.time()]):
            nonlocal denoise_time
            if job.cancel:
                raise Cancelled()
            now = time.time()
            if s > 1:
                denoise_time += now - _t[0]
                job.done_steps += 1
                job.sec_per_step = denoise_time / job.done_steps
            _t[0] = now
            job.step = s

        try:
            frames = ENGINE.segment(prompt, image, w, h, job.steps, job.guidance, job.seed + i, on_step)
        except RuntimeError as e:
            if "NAN_RESULT" not in str(e) or not ENGINE.to_bf16():
                raise
            job.msg = f"كنعاود القطعة {i + 1} بدقة أخرى…"
            frames = ENGINE.segment(prompt, image, w, h, job.steps, job.guidance, job.seed + i, on_step)
        job.extra_per_seg = time.time() - t_seg - (job.sec_per_step or 0) * job.steps
        if first_frame is None:
            first_frame = Image.fromarray(frames[0])
        last = Image.fromarray(frames[-1])
        part = os.path.join(folder, f"part_{i + 1:02d}.mp4")
        write_mp4(frames if i == 0 else frames[1:], part)
        parts.append(part)
        concat_mp4(parts, final)
        job.out = final
        image = match_color(last, first_frame, 0.5) if job.colorfix else last
        del frames

    job.state = "done"
    job.msg = f"✅ الفيديو واجد (رقم البذرة: {job.seed})"
    shutil.rmtree(folder, ignore_errors=True)


def worker():
    while True:
        job = Q.get()
        if job.cancel:
            job.state, job.msg = "cancelled", "⏹️ تلغى"
            continue
        while not ENGINE.ready and ENGINE.error is None:
            job.msg = "كنتسناو الموديل يتحمّل…"
            time.sleep(2)
        if ENGINE.error:
            job.state, job.msg = "error", ENGINE.status
            continue
        try:
            try:
                run_job(job)
            except Exception as e:
                if not is_oom(e) or job.quality == Q_FAST:
                    raise
                log(f"[{job.id}] OOM at {job.quality} → retry at {Q_FAST}")
                free_gpu()
                job.quality, job.steps = Q_FAST, min(job.steps, QUALITY[Q_FAST]["steps"])
                job.seg_i = job.step = job.done_steps = 0
                job.sec_per_step, job.out = None, None
                job.note = "ℹ️ الجودة العالية ما دخلاتش فالذاكرة، تصاوب بالسريعة."
                run_job(job)
                job.msg += " " + job.note
            notify("🎬 الفيديو واجد", f"فيديو ديال {job.n_seg * 5} ثانية تصاوب. دخل حمّلو.", STATE["url"], ["clapper"], 4)
        except Cancelled:
            job.state = "cancelled"
            job.msg = "⏹️ توقف" + (" — الجزء اللي تصاوب محفوظ" if job.out else "")
        except Exception as e:
            job.state = "error"
            s = str(e)
            if is_oom(e):
                job.msg = "❌ الذاكرة ما كفاتش. اختار الجودة «سريعة» وعاود."
            elif "NAN_RESULT" in s:
                job.msg = "❌ النتيجة خرجات خاوية. عاود بـ «رقم البذرة» آخر ولا بالجودة «سريعة»."
            else:
                job.msg = f"❌ وقع مشكل: {e}"
            traceback.print_exc()
            notify("❌ الفيديو ما تصاوبش", job.msg, STATE["url"], ["x"])
            free_gpu()
        touch()
        log(f"[{job.id}] {job.state}: {job.msg}")


def is_oom(e):
    return "out of memory" in str(e).lower() or type(e).__name__ == "OutOfMemoryError"


def free_gpu():
    try:
        ENGINE.vae.to("cpu")
        ENGINE.torch.cuda.empty_cache()
    except Exception:
        pass


def busy():
    return any(j.state in ("queued", "running") for j in JOBS)


def shutdown(reason):
    log("shutdown:", reason)
    notify("🔌 التطبيق طفا", reason + " الفيديوهات محفوظين فـ Output ديال Kaggle.\n"
           "باش تعاود تشعلو: Kaggle ← النوتبوك ديالك ← Save Version ← Save & Run All.",
           "https://www.kaggle.com/code", ["electric_plug"])
    time.sleep(1)
    os._exit(0)


def idle_watchdog():
    while True:
        time.sleep(30)
        if IDLE_MINUTES > 0 and not busy() and time.time() - STATE["last_activity"] > IDLE_MINUTES * 60:
            shutdown(f"ما تستعملش {int(IDLE_MINUTES)} دقيقة، طفيتو باش توفر الساعات ديال GPU.")


def fmt_min(sec):
    if sec is None:
        return "كيتحسب…"
    m = int(round(sec / 60))
    if m < 1:
        return "أقل من دقيقة"
    if m < 60:
        return f"{m} دقيقة"
    return f"{m // 60} ساعة و{m % 60} دقيقة"


def eta(job):
    if job.state != "running" or not job.sec_per_step:
        return None
    remaining_steps = (job.n_seg - job.seg_i) * job.steps + (job.steps - job.step)
    return remaining_steps * job.sec_per_step + (job.n_seg - job.seg_i + 1) * max(0, getattr(job, "extra_per_seg", 30))


# ----------------------------------------------------------------------------
# الواجهة (نفس الروح ديال Yollo، بلا جواهر بلا اشتراك)
# ----------------------------------------------------------------------------
def submit(image, prompt, duration, quality, aspect, steps, guidance, seed, translate, colorfix, _dedupe=True):
    touch()
    lines = [l.strip() for l in (prompt or "").splitlines() if l.strip()]
    sig = (getattr(image, "size", None), tuple(lines), duration, quality, aspect)
    for j in JOBS[-5:]:
        if (_dedupe and j.state in ("queued", "running") and getattr(j, "sig", None) == sig and seed in (None, -1)
                and time.time() - j.created < 20):
            return "⏳ هاد الطلب ديجا فاللائحة (ما تضغطش جوج مرات)."
    if not lines:
        if image is None:
            return "⚠️ كتب الموجهات (صف الفيديو) ولا زيد صورة."
        lines = [DEFAULT_PROMPT]
    n_seg = max(1, int(round(float(duration) / SEG_SECONDS)))
    seed = int(seed) if seed is not None and int(seed) >= 0 else random.randint(0, 2**31 - 1)
    job = Job(image=image, prompts=lines, n_seg=n_seg, quality=quality, aspect=aspect, steps=int(steps),
              guidance=float(guidance), seed=seed, translate=bool(translate), colorfix=bool(colorfix))
    job.sig, job.created = sig, time.time()
    JOBS.append(job)
    LAST.clear()
    LAST.update(image=image, prompt=prompt, duration=duration, quality=quality, aspect=aspect, steps=steps,
                guidance=guidance, translate=translate, colorfix=colorfix)
    Q.put(job)
    ahead = sum(1 for j in JOBS if j.state in ("queued", "running")) - 1
    return f"✅ تزاد الطلب: {n_seg * 5} ثانية. " + (f"قدامك {ahead} فاللائحة." if ahead else "بدا دابا.")


def again():
    """نفس الصورة، نفس الوصف، نفس المدة والجودة… غير البذرة كتبدل باش تخرج نسخة مختلفة."""
    touch()
    if not LAST:
        return "⚠️ مازال ما صاوبتي حتى فيديو. صاوب واحد الأول ومن بعد عاود."
    return "🔁 نسخة أخرى بنفس الإعدادات — " + submit(**LAST, seed=-1, _dedupe=False)


def cancel_all():
    touch()
    n = 0
    for j in JOBS:
        if j.state in ("queued", "running"):
            j.cancel = True
            n += 1
    return f"⏹️ غادي يتوقف ({n})" if n else "ما كاين حتى طلب خدام."


def status_md():
    st = ENGINE.status
    if not ENGINE.ready and ENGINE.error is None and getattr(ENGINE, "t_load", None):
        st += f" (دازت {int((time.time() - ENGINE.t_load) // 60)} دقيقة)"
    lines = [f"**المحرك:** {st}"]
    active = [j for j in JOBS if j.state in ("queued", "running")]
    for j in active:
        if j.state == "running":
            pct = int(100 * ((j.seg_i - 1) * j.steps + j.step) / max(1, j.n_seg * j.steps))
            lines.append(f"🎬 **{j.msg}** — **{pct}%** — باقي تقريباً: **{fmt_min(eta(j))}**")
        else:
            lines.append(f"⏳ طلب فاللائحة ({j.n_seg * 5} ثانية) — {j.msg}")
    last = [j for j in JOBS if j.state in ("done", "error", "cancelled")][-1:]
    for j in last:
        lines.append(f"**آخر طلب:** {j.msg}")
    return "  \n".join(lines)


def list_videos():
    if not os.path.isdir(OUT_DIR):
        return []
    files = [os.path.join(OUT_DIR, f) for f in os.listdir(OUT_DIR) if f.endswith(".mp4")]
    return sorted(files, key=os.path.getmtime, reverse=True)


def latest_video():
    for j in reversed(JOBS):
        if j.out and os.path.exists(j.out):
            return j.out
    v = list_videos()
    return v[0] if v else None


CSS = """
.gradio-container {direction: rtl; max-width: 680px !important; margin: auto;}
.gradio-container input, .gradio-container textarea {text-align: right;}
#hdr h1 {font-size: 1.45em; margin: 0;}
.gen-btn {background: linear-gradient(90deg, #7c3aed, #c026d3, #db2777) !important; color: #fff !important;
          font-size: 1.2em !important; min-height: 56px; border-radius: 16px !important; border: none !important;}
.tabs button[role=tab] {font-size: 1.02em;}
.tabs button[role=tab][aria-selected=true] {background: linear-gradient(90deg, #4f46e5, #9333ea); color: #fff !important;
          border-radius: 12px;}
#status {border-radius: 12px; padding: 6px 10px; background: rgba(147, 51, 234, .12);}
footer {display: none !important;}
"""
HEAD = "<script>document.addEventListener('DOMContentLoaded',()=>document.body.classList.add('dark'));</script>"


def make_theme():
    import gradio as gr

    return gr.themes.Soft(primary_hue="purple", secondary_hue="pink", radius_size="lg").set(
        body_background_fill_dark="#0e0e14",
        block_background_fill_dark="#1a1a24",
        input_background_fill_dark="#2a2a36",
        block_label_background_fill_dark="#2a2a36",
        button_primary_background_fill_dark="linear-gradient(90deg, #7c3aed, #db2777)",
        button_primary_background_fill_hover_dark="linear-gradient(90deg, #6d28d9, #be185d)",
    )


def build_ui():
    import gradio as gr

    with gr.Blocks(title="فيديو بالذكاء الاصطناعي") as demo:
        gr.Markdown("# ✨ فيديو بالذكاء الاصطناعي\nإنشائي · فابور · بلا حدود", rtl=True, elem_id="hdr")
        status = gr.Markdown(status_md(), rtl=True, elem_id="status")
        info = gr.Markdown(rtl=True)

        with gr.Tabs(elem_classes="tabs"):
            with gr.Tab("🖼️ صورة إلى فيديو"):
                image = gr.Image(label="الصورة", type="pil", sources=["upload"], height=260)
                prompt_i = gr.Textbox(label="الموجهات *", placeholder="صف الحركة اللي بغيتي فالفيديو…\n"
                                      "(كل سطر = 5 ثواني)", lines=4, max_length=5000, rtl=True)
                go_i = gr.Button("✨ إنشاء", elem_classes="gen-btn")
            with gr.Tab("✍️ نص إلى فيديو"):
                prompt_t = gr.Textbox(label="الموجهات *", placeholder="صف الفيديو الذي تريد إنشاءه…\n"
                                      "(كل سطر = 5 ثواني)", lines=5, max_length=5000, rtl=True)
                aspect = gr.Radio(ASPECTS, value=ASPECTS[0], label="📐 الشكل")
                go_t = gr.Button("✨ إنشاء", elem_classes="gen-btn")

        duration = gr.Radio(DURATIONS, value=10, label="⏱️ المدة (ثواني)")
        quality = gr.Radio([Q_HIGH, Q_FAST], value=Q_HIGH, label="🎞️ الجودة",
                           info="العالية أوضح ولكن أبطأ بزاف (تقريباً 3 مرات). للتجربة الأولى اختار السريعة.")
        with gr.Accordion("⚙️ إعدادات متقدمة", open=False):
            steps = gr.Slider(15, 50, value=QUALITY[Q_HIGH]["steps"], step=1, label="عدد الخطوات (كثر = أدق وأبطأ)")
            guidance = gr.Slider(2.0, 8.0, value=5.0, step=0.5, label="قوة الالتزام بالوصف")
            seed = gr.Number(value=-1, precision=0, label="رقم البذرة (-1 = عشوائي)")
            translate = gr.Checkbox(value=True, label="ترجم الوصف للإنجليزية أوتوماتيكياً (أحسن نتيجة)")
            colorfix = gr.Checkbox(value=True, label="ثبّت الألوان بين القطع")
        quality.change(lambda q: QUALITY[q]["steps"], quality, steps)

        gr.Markdown("### 🎬 إنشائي", rtl=True)
        video = gr.Video(label="آخر فيديو (كيتحدّث مع كل قطعة)", value=latest_video())
        again_btn = gr.Button("🔁 عاود بنفس الإعدادات (نسخة أخرى)", elem_classes="gen-btn")
        files = gr.File(label="⬇️ الفيديوهات ديالك (كليكي باش تحمّل)", file_count="multiple",
                        value=list_videos(), interactive=False)
        with gr.Row():
            refresh = gr.Button("🔄 تحديث")
            stop = gr.Button("⏹️ وقف الطلب")
        off = gr.Button("🔌 طفي التطبيق (باش توفر الساعات)", variant="stop")
        gr.Markdown("ℹ️ تقدر تسد التليفون، الخدمة كتكمل وكيجيك إشعار ملي يوجد الفيديو.", rtl=True)

        shown = gr.State({"video": latest_video(), "files": tuple(list_videos())})

        def tick(st):
            touch()
            st = dict(st or {})
            v, fl = latest_video(), tuple(list_videos())
            out_v, out_f = gr.skip(), gr.skip()
            if v != st.get("video"):
                out_v, st["video"] = v, v
            if fl != st.get("files"):
                out_f, st["files"] = list(fl), fl
            return status_md(), out_v, out_f, st

        def sub_image(img, p, d, q, s, g, sd, tr, cf):
            if img is None:
                return "⚠️ زيد الصورة، ولا استعمل «نص إلى فيديو»."
            return submit(img, p, d, q, ASPECTS[0], s, g, sd, tr, cf)

        def sub_text(p, a, d, q, s, g, sd, tr, cf):
            return submit(None, p, d, q, a, s, g, sd, tr, cf)

        def turn_off():
            threading.Thread(target=shutdown, args=("طفيتيه من الزر.",), daemon=True).start()
            return "🔌 كيطفى… الفيديوهات محفوظين فـ Output ديال Kaggle."

        outs = [status, video, files, shown]
        adv = [duration, quality, steps, guidance, seed, translate, colorfix]
        go_i.click(sub_image, [image, prompt_i] + adv, info).then(tick, shown, outs)
        go_t.click(sub_text, [prompt_t, aspect] + adv, info).then(tick, shown, outs)
        stop.click(cancel_all, None, info)
        again_btn.click(again, None, info).then(tick, shown, outs)
        off.click(turn_off, None, info)
        refresh.click(tick, shown, outs)
        gr.Timer(8).tick(tick, shown, outs)
        demo.load(tick, shown, outs)
    return demo


# ----------------------------------------------------------------------------
# الرابط العام (Gradio، وإلا Cloudflare كاحتياط)
# ----------------------------------------------------------------------------
TRY_CF = re.compile(r"https://(?!api\.)[a-z0-9]+(?:-[a-z0-9]+)+\.trycloudflare\.com")  # ماشي رسائل الخطأ ديال api.


def cloudflare_tunnel(port, timeout=90):
    exe = "/tmp/cloudflared"
    if not os.path.exists(exe):
        import urllib.request

        urllib.request.urlretrieve(
            "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64", exe)
        os.chmod(exe, 0o755)
    p = subprocess.Popen([exe, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    found = {}

    def reader():
        for line in p.stdout:
            m = TRY_CF.search(line)
            if m and "url" not in found:
                found["url"] = m.group(0)

    threading.Thread(target=reader, daemon=True).start()
    t = time.time()
    while "url" not in found and time.time() - t < timeout and p.poll() is None:
        time.sleep(0.5)
    return found.get("url")


def start_background(components=None):
    os.makedirs(OUT_DIR, exist_ok=True)
    threading.Thread(target=ENGINE.load, kwargs={"components": components}, daemon=True).start()
    threading.Thread(target=worker, daemon=True).start()


def main():
    start_background()
    demo = build_ui()
    demo.queue(default_concurrency_limit=4)
    # إلا ما خدمش الرابط ديال Gradio كيرجع None (بلا ما يطيح)، وكنجربو Cloudflare
    _, local_url, url = demo.launch(share=os.environ.get("VIDEO_APP_SHARE", "1") == "1", prevent_thread_lock=True,
                                    allowed_paths=[OUT_DIR], css=CSS, theme=make_theme(), head=HEAD,
                                    footer_links=[], show_error=True, server_port=PORT)
    if not url and os.environ.get("VIDEO_APP_SHARE", "1") == "1" and os.environ.get("VIDEO_APP_CF", "1") == "1":
        log("Gradio share failed → trying Cloudflare tunnel")
        try:
            url = cloudflare_tunnel(PORT)
        except Exception as e:
            log("cloudflare failed:", e)
    if url:
        url = url.rstrip("/") + "/?__theme=dark"
        STATE["url"] = url
        notify("🔗 التطبيق خدام", "كليكي هنا باش تحل التطبيق. (الموديل كيتحمّل، كيجيك إشعار ملي يوجد)", url, ["link"], 4)
    bar = "=" * 60
    print(f"\n{bar}\n🔗 الرابط ديال التطبيق (حلّو فالتليفون):\n\n    {url or '❌ ما قدرتش نصاوب رابط عام'}\n")
    if NTFY_TOPIC:
        print(f"📌 الرابط الثابت ديالك (ديما فيه آخر رابط):  https://ntfy.sh/{NTFY_TOPIC}\n")
    print(f"كيطفى بوحدو إلا ما تستعملش {int(IDLE_MINUTES)} دقيقة (من بعد ما يوجد الموديل).\n{bar}\n", flush=True)
    threading.Thread(target=idle_watchdog, daemon=True).start()
    demo.block_thread()


if __name__ == "__main__":
    main()
