#!/bin/sh
# يبني صفحة الأرتيفاكت ونسخة المستودع من القالب والبيانات
set -e
cd "$(dirname "$0")"
python3 -I - <<'PY'
s=open('src/app.html',encoding='utf-8').read(); d=open('data/data.json',encoding='utf-8').read()
page=s.replace('/*DATA*/',d)
open('dist/khushu.html','w',encoding='utf-8').write(page)
head='''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#1f4d3f">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="icon-192.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}[hidden]{display:none!important}</style>
'''
t='<title>مكتبتي</title>\n'
body=page.replace(t,'',1)
reg='''
<script>if('serviceWorker' in navigator){addEventListener('load',()=>navigator.serviceWorker.register('sw.js'))}</script>
</body></html>
'''
open('../Maktabati/index.html','w',encoding='utf-8').write(head+t+'</head>\n<body>\n'+body+reg)
PY
