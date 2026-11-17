# Optimization: analysis aur plan

Sab numbers isi Mac par (Apple M5, llama3.2 3B Q4_K_M, 100% GPU) naape gaye, temporary database par. 8 Nov 2026.

## 1. Samay kahan jaata hai (ek assistant turn)

| Hissa | Samay | Note |
|---|---|---|
| Router + tareekh + database | ~1–3 ms | Rukawat nahi. Ek DB connection ~0.2 ms |
| Model: prompt padhna (796 tokens) | **~1,200 ms** | Sabse bada hissa, aur cache se bachaya ja sakta tha |
| Model: tool call likhna (~30 tokens) | ~1,100 ms | ~27 tokens/s. Isse chhota karne ki gunjaish kam |
| Tool chalana + jawab (code se) | ~1 ms | |
| Saare 18 tools ke saath prompt | 1,797 tokens, ~2,400 ms | Router pehle se isse aadha kar raha tha |
| API (`/api/stats`, `/api/overview`) | 4–8 ms, 1–6 KB | Theek |
| Memory | Ollama ~2.7 GB, whisper-server ~650 MB, dashboard ~25 MB | |

**Sabse badi khoj:** system prompt mein *minute* tak ka samay tha, isliye har turn par Ollama ka KV-cache toot jaata tha aur poora prompt dobara padha jaata tha. Wahi prompt dobara bhejne par prompt-processing **1,200 ms se 35 ms** ho jaati hai.

## 2. Jo kar diya (naape hue nateeje ke saath)

| # | Kya | Nateeja |
|---|---|---|
| 1 | System prompt din bhar ek jaisa (sirf tareekh). Samay ka hint aakhri user message ke saath | Alag sawalon par prompt-processing ~1,160 ms se **~200 ms**. Eval average **1,955 ms se 1,201 ms**, accuracy 40/40 wahi |
| 2 | SQLite: schema/migration har process mein ek baar, **WAL mode**, 10 s busy-timeout | Threads (dashboard, reminder loop, CLI) ek saath safe. Har connection par schema script band |
| 3 | `llm.is_running()` ka 10 s cache | Har stats poll par Ollama ping band. Ollama band ho to 1.5 s ka atkav bhi nahi |
| 4 | Stats polling: System tab par 5 s, baaki jagah 15 s | ~66% kam requests jab System tab band ho |
| 5 | Awaaz: recording ka 16 kHz downsample incremental | Pehle har partial par poori recording dobara (O(n²)). Ab sirf naya hissa. Output bit-for-bit same (test kiya) |
| 6 | Whisper turbo + dynamic `audio_ctx` | Turbo model 2.0 s se **~0.55 s** har clip, accuracy small se behtar |
| 7 | Chat history table 500 baaton tak | Database hamesha ke liye nahi badhta |
| 8 | Bhatke whisper-server: sirf anaath (parent mar chuka) wale band | Do dashboard ek saath chalein to ek doosre ka server nahi maarega |
| 9 | Router: 18 mein se 1–3 tools | Prompt ~2× chhota (pehle se tha, naap se pakka) |

## 3. Aage kya (priority ke hisaab se)

### P1: achha fayda, thoda kaam
1. **Bina model ke aur shortcuts.** Abhi ~25% baatein instant hain. Jaise "X kar li", "paani piya" (number ke saath), "Y done" ko pakke pattern se seedha tool par bhejna. *Ummeed:* aise turns 1.2 s se ~5 ms. *Jaanch:* `run_agent_eval.py` mein instant % aur accuracy.
2. **Conversation mein history ka cache.** Ab system prompt cache ho raha hai. Agla kadam: `MAX_HISTORY` ke saath purane tool messages ko chhota karna (jaise lambe search_notes passages history mein na rakhna), taaki prefix lamba aur sasta rahe. *Jaanch:* 5-turn conversation mein `prompt_eval_duration`.
3. **Notes ka jawab streaming mein (assistant tab mein bhi).** Abhi notes wala jawab poora banne ke baad dikhta hai (~2 s). Streaming se pehla shabd ~0.5 s mein. *Jaanch:* "first word" time.
4. **Unit tests (stdlib `unittest`).** Sabse pehle `when.parse`, `router.route`, `agent._decision`, `planner.clean_title`, `voice.correct` aur delete safety. Ye sab bina model ke, milliseconds mein chalte hain. Har badlav par 1 second mein pata chalega ki kuch toota to nahi.

### P2: baad mein
5. **`num_ctx` 8192 se 4096:** ~0.45 GB memory bachegi. Abhi zaroorat nahi (RAM kaafi hai), aur lamba notes context kat sakta hai. Pehle sabse lamba asli prompt naapo.
6. **Ek hi whisper-server, kai dashboards ke liye:** sirf tab, jab aap aksar 2 dashboard ek saath chalate ho.
7. **Bada model (llama3.1 8B ya qwen2.5 7B):** accuracy shayad behtar, par har turn ~2–3× dheema aur ~5 GB memory. Abhi 3B + router + code-checks se 100% eval hai, isliye zaroorat nahi.

## 4. Jo NAHI karna (aur kyun)
- **Har DB connection ko "optimize" karna:** 0.2 ms hai. Fayda naapne layak nahi.
- **AUTOINCREMENT ke liye tables dobara banana:** delete ki suraksha ab id + naam dono milane se hai. Table rebuild mein foreign keys ki wajah se habit check-ins aur nicknames mit sakte hain.
- **Prompt aur lamba karna "accuracy ke liye":** har 1,000 tokens ~1.4 s. Pakke niyam code mein (router, when.py, repair) zyada tez aur bharose wale hain.

## Kaise dobara naapein
```
python3 run_agent_eval.py                         # accuracy + average time (40 cases)
python3 run_agent_eval.py agent_eval_blind.json   # bilkul nayi lines
python3 run_eval.py                               # notes
```
