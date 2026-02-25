import Swal from 'sweetalert2'

export const showAlert = (title: string, text?: string, icon: 'info' | 'success' | 'warning' | 'error' = 'info') => {
  return Swal.fire({ title, text, icon })
}

export const showConfirm = async (title: string, text?: string) => {
  const res = await Swal.fire({
    title,
    text,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Yes',
    cancelButtonText: 'Cancel'
  })
  return !!res.isConfirmed
}

export const showLoading = (title = 'Please wait') => {
  Swal.fire({
    title,
    html: '<div style="margin-top:8px">Processing...</div>',
    allowOutsideClick: false,
    didOpen: () => {
      Swal.showLoading()
    }
  })
}

export const closeSwal = () => Swal.close()
