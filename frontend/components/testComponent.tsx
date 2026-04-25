"use client"
import { useEffect, useState } from "react";

const TestComponent = () => {
    const [data, setData] = useState(null)
    const [mounted, setMounted] = useState(false)

    useEffect(() => {
        setMounted(true)
        fetch('http://127.0.0.1:8000/')
        .then(res => res.json())
        .then(data => setData(data.message))
    }, [])

  if (!mounted) return null

  return (
    <div>
         Backend sagt: {data || "Lädt..."} ----- 
    </div>
  )
}

export default TestComponent