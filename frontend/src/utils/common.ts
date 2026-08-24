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
