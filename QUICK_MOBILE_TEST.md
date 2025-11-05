# 🎯 QUICK MOBILE TEST (5 Minutes)

## ⚡ Fast Verification Steps

**URL:** Your Render deployment URL + `/count.html`

---

## Test #1: Fullscreen Camera ⏱️ 1 min
1. Open on mobile
2. Click "Kamera Aç"
3. **Check:** Camera fills entire screen?
   - ✓ YES → Continue
   - ✗ NO → See troubleshooting below

---

## Test #2: Green Frame ⏱️ 1 min
1. Look at center of camera screen
2. **Check:** Green border frame visible around center?
   - ✓ YES (green, centered, ~75% screen) → Continue
   - ✗ NO → See troubleshooting below

---

## Test #3: Scan & Message ⏱️ 2 min
1. Scan any QR code
2. **Check:** Green message appears at TOP of screen?
   - ✓ YES ("QR okundu") → Continue
   - ✗ NO (message hidden behind camera) → See troubleshooting

3. Wait 3 seconds, message fades
4. Scan SAME QR again immediately (within 2 seconds)
5. **Check:** Red message "QR zaten okundu"?
   - ✓ YES (red, duplicate prevented) → ✅ ALL GOOD
   - ✗ NO (green message again) → See troubleshooting

---

## Test #4: Database Check ⏱️ 1 min
After scanning 3-5 different QRs:

```sql
SELECT COUNT(*) FROM scanned_qr WHERE session_id = 'YOUR_SESSION_ID';
```

**Expected:** 3-5 records (no duplicates, even if same QR scanned multiple times)

---

## 🔴 TROUBLESHOOTING

### ❌ Camera not fullscreen?
**Check:**
```
Browser DevTools > Elements > #reader
Should have: position: fixed; z-index: 10; height: 100dvh; width: 100vw;
```

**Fix:** 
- Hard refresh (Ctrl+Shift+R on desktop, pull-down refresh on mobile)
- Clear browser cache
- Check commit `1b99085` deployed to Render

---

### ❌ Green frame not visible?
**Check:**
```
Browser DevTools > Elements > .qr-scan-frame
Should have: z-index: 999; border: 3px solid #28a745;
```

**Fix:**
- Frame should be behind camera (z-index 999 < 1000 for messages)
- Try scanning to see if frame appears
- Check browser console for errors

---

### ❌ Message not appearing at top?
**Check:**
```
Browser DevTools > Elements > .scan-messages
Should have: position: fixed; top: 20px; z-index: 1000; pointer-events: auto;
```

**Fix:**
- Scan again - message should appear in 0.5s
- Check browser console for JavaScript errors
- Verify WebSocket connected (should show in Network tab)

---

### ❌ Duplicate message not red?
**Check:**
```
Browser DevTools > Console
Scan same QR twice within 2 seconds
Should show: "2s debounce active" messages
```

**Fix:**
- Wait 2 seconds between duplicates (outside debounce window)
- Check `scanned_qr` table for duplicate records in database

---

## 📊 Quick Result Summary

```
Device: _______________
Result: ✅ PASS / ❌ FAIL

Fullscreen:     ✓ ✗
Green frame:    ✓ ✗  
Top message:    ✓ ✗
Red duplicate:  ✓ ✗
DB clean:       ✓ ✗
```

---

## 🚀 If ALL Tests PASS ✅

**Deployment is SUCCESSFUL!** 🎉

Next steps:
1. Run main application end-to-end test
2. Verify with real QR codes
3. Check activity logs
4. Monitor for errors in Render logs

---

## 🛠️ If Any Test FAILS ❌

**Immediate Actions:**
1. Collect screenshot of issue
2. Run: `git log --oneline -5` (verify commit 1b99085 is latest)
3. Check Render deployment logs
4. Hard refresh browser cache
5. Try incognito/private browsing mode
6. Test on different device/browser

**Then:**
- Report specific failing test #
- Share browser console screenshot
- Share DevTools element inspection

---

**Expected Pass Rate:** 99%+
**Estimated Test Time:** 5-10 minutes
**Live Render Deployment Time:** 2-5 minutes after git push
