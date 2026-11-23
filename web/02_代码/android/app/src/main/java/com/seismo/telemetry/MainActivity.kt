package com.seismo.telemetry

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.ViewGroup
import android.view.WindowManager
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.TextView

/**
 * 震感捕手 · 遥测端
 *
 * K10 上跑 Web 服务器（/api/now、/api/wave、/api/record、/api/last），
 * 这个 App 全屏加载 K10 的网页控制台，并自动尝试几个常见地址：
 *   1. 上次成功的地址
 *   2. seismo.local（mDNS，K10 换 IP 也能找到）
 *   3. 192.168.4.1（K10 热点模式）
 *
 * 长按屏幕可手动改地址；全部失败时点屏幕中央提示也能改。
 */
class MainActivity : Activity() {

    private lateinit var web: WebView
    private lateinit var prefs: android.content.SharedPreferences
    private lateinit var overlay: TextView

    private val candidates = ArrayList<String>()
    private var attempt = 0
    private var current = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        prefs = getSharedPreferences("seismo", Context.MODE_PRIVATE)

        val root = FrameLayout(this)

        web = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.cacheMode = WebSettings.LOAD_NO_CACHE
            settings.mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            settings.useWideViewPort = true
            settings.loadWithOverviewMode = true
            setBackgroundColor(0xFF0B1220.toInt())
            webViewClient = object : WebViewClient() {
                override fun onReceivedError(
                    view: WebView,
                    request: WebResourceRequest,
                    error: WebResourceError
                ) {
                    if (request.isForMainFrame) tryNext()
                }
            }
        }
        root.addView(
            web,
            FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        )

        overlay = TextView(this).apply {
            setTextColor(0xFFE5E7EB.toInt())
            setBackgroundColor(0xFF0B1220.toInt())
            textSize = 15f
            gravity = Gravity.CENTER
            visibility = android.view.View.GONE
            setPadding(48, 48, 48, 48)
            setOnClickListener { askHost() }
        }
        root.addView(
            overlay,
            FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        )

        web.setOnLongClickListener { askHost(); true }
        root.setOnLongClickListener { askHost(); true }

        setContentView(root)
        startConnect()
    }

    private fun startConnect() {
        candidates.clear()
        val saved = prefs.getString("host", "") ?: ""
        if (saved.isNotEmpty()) candidates.add(saved)
        if (!candidates.contains("seismo.local")) candidates.add("seismo.local")
        if (!candidates.contains("192.168.4.1")) candidates.add("192.168.4.1")
        attempt = 0
        overlay.visibility = android.view.View.GONE
        tryNext()
    }

    private fun tryNext() {
        if (attempt >= candidates.size) {
            showFail()
            return
        }
        current = candidates[attempt++]
        web.loadUrl(normalize(current))
    }

    private fun normalize(h: String): String {
        val host = h.trim()
        if (host.startsWith("http")) return if (host.endsWith("/")) host else "$host/"
        return "http://$host/"
    }

    private fun showFail() {
        overlay.text = """连不上 K10

试过：${candidates.joinToString("、")}

1. 手机要和 K10 在同一 WiFi；K10 热点模式时连 K10-Seismo-Setup
2. 看 K10 屏幕上第 5 行显示的 IP，长按这里填进去
3. 路由器开了"AP 隔离"的话，手机也连不上

点这里改地址"""
        overlay.visibility = android.view.View.VISIBLE
    }

    private fun askHost() {
        val input = EditText(this).apply {
            hint = "192.168.4.1"
            inputType = InputType.TYPE_CLASS_TEXT
            setText(if (current.isEmpty()) "192.168.4.1" else current)
            setSelectAllOnFocus(true)
        }
        AlertDialog.Builder(this)
            .setTitle("K10 地址")
            .setMessage("看 K10 屏幕第 5 行。热点模式是 192.168.4.1；连路由器后是一个 192.168.x.x，也可以填 seismo.local")
            .setView(input)
            .setPositiveButton("连接") { _, _ ->
                val h = input.text.toString().trim()
                if (h.isEmpty()) return@setPositiveButton
                prefs.edit().putString("host", h).apply()
                candidates.clear()
                candidates.add(h)
                if (!candidates.contains("seismo.local")) candidates.add("seismo.local")
                attempt = 0
                overlay.visibility = android.view.View.GONE
                tryNext()
            }
            .setNegativeButton("取消", null)
            .show()
    }

    override fun onBackPressed() {
        if (web.canGoBack()) web.goBack() else finish()
    }

    override fun onDestroy() {
        web.destroy()
        super.onDestroy()
    }
}
