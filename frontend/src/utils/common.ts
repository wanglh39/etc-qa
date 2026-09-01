// 时间格式化
export const formatTime = () => {
  const date = new Date()
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const h = String(date.getHours()).padStart(2, '0')
  const m = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${h}:${m}`
}
// 树形数据扁平化（分类树用）
export const flattenTree = (tree: any[], key = 'children') => {
  let res: any[] = []
  tree.forEach((item) => {
    res.push(item)
    if (item[key] && item[key].length) {
      res = res.concat(flattenTree(item[key], key))
    }
  })
  return res
}

// 复制文本到剪贴板：优先 Clipboard API（仅 HTTPS/localhost 可用），HTTP 环境降级 execCommand
export const copyText = async (text: string): Promise<boolean> => {
  if (navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // 落入降级分支
    }
  }
  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    textarea.style.top = '0'
    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(textarea)
    return ok
  } catch {
    return false
  }
}
