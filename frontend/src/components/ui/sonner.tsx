import * as React from "react"
import { Toaster as Sonner, ToasterProps } from "sonner"
import { useTheme } from "../../context/ThemeContext"

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme } = useTheme()

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      toastOptions={{
        classNames: {
          toast: '!bg-white dark:!bg-gray-800 !text-gray-900 dark:!text-gray-100 !border-gray-200 dark:!border-gray-700 !shadow-lg',
          title: '!text-gray-900 dark:!text-gray-100 !font-medium',
          description: '!text-gray-600 dark:!text-gray-300',
          actionButton: '!bg-amber-500 !text-white hover:!bg-amber-600',
          cancelButton: '!bg-gray-100 dark:!bg-gray-700 !text-gray-600 dark:!text-gray-300 hover:!bg-gray-200 dark:hover:!bg-gray-600',
          closeButton: '!text-gray-500 dark:!text-gray-400 hover:!text-gray-700 dark:hover:!text-gray-200',
          error: '!bg-red-50 dark:!bg-red-900/20 !text-red-800 dark:!text-red-200 !border-red-200 dark:!border-red-800',
          success: '!bg-green-50 dark:!bg-green-900/20 !text-green-800 dark:!text-green-200 !border-green-200 dark:!border-green-800',
          warning: '!bg-yellow-50 dark:!bg-yellow-900/20 !text-yellow-800 dark:!text-yellow-200 !border-yellow-200 dark:!border-yellow-800',
          info: '!bg-blue-50 dark:!bg-blue-900/20 !text-blue-800 dark:!text-blue-200 !border-blue-200 dark:!border-blue-800',
        },
        style: {
          backgroundColor: theme === 'dark' ? '#374151' : '#ffffff',
          color: theme === 'dark' ? '#f3f4f6' : '#111827',
          border: theme === 'dark' ? '1px solid #4b5563' : '1px solid #e5e7eb',
        }
      }}
      {...props}
    />
  )
}

export { Toaster }